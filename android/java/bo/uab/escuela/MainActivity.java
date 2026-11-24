package bo.uab.escuela;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.text.InputType;
import android.view.Menu;
import android.view.MenuItem;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.SslErrorHandler;
import android.webkit.URLUtil;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Toast;

import java.net.URI;
import java.util.HashSet;
import java.util.Set;

/**
 * Cliente Android de la Escuela de Fútbol UAB.
 *
 * La app es un contenedor WebView: los datos siguen en la PC (Flask + SQLite)
 * y el celular solo muestra el panel por WiFi/LAN. La dirección del servidor
 * se configura desde el menú y queda guardada en el dispositivo.
 */
public class MainActivity extends Activity {

    private static final String PREFS = "escuela_uab";
    private static final String CLAVE_URL = "url_servidor";
    private static final String CLAVE_HOSTS = "hosts_confiables";
    private static final String URL_POR_DEFECTO = "https://172.17.33.202:5443/escuela";

    private static final int CODIGO_CAMARA = 1001;
    private static final int CODIGO_ALMACENAMIENTO = 1002;

    private static final int MENU_RECARGAR = Menu.FIRST;
    private static final int MENU_SERVIDOR = Menu.FIRST + 1;
    private static final int MENU_CERTIFICADO = Menu.FIRST + 2;
    private static final int MENU_NAVEGADOR = Menu.FIRST + 3;
    private static final int MENU_ACERCA = Menu.FIRST + 4;

    private WebView webView;
    private SharedPreferences prefs;
    private PermissionRequest permisoPendiente;
    private String descargaUrl;
    private String descargaUserAgent;
    private String descargaNombre;
    private String descargaMime;
    private long ultimoAtras = 0L;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        FrameLayout contenedor = new FrameLayout(this);
        webView = new WebView(this);
        contenedor.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(contenedor);

        configurarWebView();

        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState);
        }

        // Primer arranque: aunque Android haya restaurado la tarea, si no hay
        // dirección guardada hay que pedirla (si no, la app queda en blanco).
        if (!prefs.contains(CLAVE_URL)) {
            if (savedInstanceState == null) {
                cargarUrl(URL_POR_DEFECTO);
            }
            mostrarDialogoServidor();
        } else if (savedInstanceState == null) {
            cargarUrl(prefs.getString(CLAVE_URL, URL_POR_DEFECTO));
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void configurarWebView() {
        WebSettings ajustes = webView.getSettings();
        ajustes.setJavaScriptEnabled(true);
        ajustes.setDomStorageEnabled(true);
        ajustes.setDatabaseEnabled(true);
        ajustes.setUseWideViewPort(true);
        ajustes.setLoadWithOverviewMode(true);
        ajustes.setMediaPlaybackRequiresUserGesture(false);
        ajustes.setAllowFileAccess(false);
        ajustes.setAllowContentAccess(false);
        ajustes.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        ajustes.setUserAgentString(ajustes.getUserAgentString() + " EscuelaUAB/1.0");

        CookieManager.getInstance().setAcceptCookie(true);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);
        }

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String esquema = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
                if (esquema.equals("http") || esquema.equals("https")) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (Exception ignored) {
                    // Sin app compatible: se ignora el enlace externo.
                }
                return true;
            }

            @Override
            public void onReceivedSslError(WebView view, final SslErrorHandler handler, SslError error) {
                String host = Uri.parse(error.getUrl()).getHost();
                if (host != null && hostsConfiables().contains(host)) {
                    handler.proceed();
                    return;
                }
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("Certificado no reconocido")
                        .setMessage("El servidor " + (host == null ? "" : host)
                                + " presenta un certificado que Android no pudo validar.\n\n"
                                + "Si es la PC de la escuela y estás en su misma WiFi, puedes continuar. "
                                + "Este permiso se recuerda para ese servidor.")
                        .setPositiveButton("Continuar", (dialogo, which) -> {
                            if (host != null) {
                                recordarHost(host);
                            }
                            handler.proceed();
                        })
                        .setNegativeButton("Cancelar", (dialogo, which) -> {
                            handler.cancel();
                            mostrarDialogoServidor();
                        })
                        .setCancelable(false)
                        .show();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    CharSequence descripcion = error.getDescription();
                    mostrarPaginaError(descripcion == null ? "" : descripcion.toString());
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> {
                    boolean pideCamara = false;
                    for (String recurso : request.getResources()) {
                        if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(recurso)) {
                            pideCamara = true;
                        }
                    }
                    if (!pideCamara) {
                        request.deny();
                        return;
                    }
                    if (checkSelfPermission(Manifest.permission.CAMERA)
                            == PackageManager.PERMISSION_GRANTED) {
                        request.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
                    } else {
                        permisoPendiente = request;
                        requestPermissions(new String[]{Manifest.permission.CAMERA}, CODIGO_CAMARA);
                    }
                });
            }
        });

        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            String nombre = URLUtil.guessFileName(url, contentDisposition, mimeType);
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q
                    && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                descargaUrl = url;
                descargaUserAgent = userAgent;
                descargaNombre = nombre;
                descargaMime = mimeType;
                requestPermissions(
                        new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE},
                        CODIGO_ALMACENAMIENTO);
                return;
            }
            iniciarDescarga(url, userAgent, nombre, mimeType);
        });

        webView.addJavascriptInterface(new PuenteWeb(), "AndroidEscuela");
    }

    private void iniciarDescarga(String url, String userAgent, String nombre, String mimeType) {
        try {
            DownloadManager.Request solicitud = new DownloadManager.Request(Uri.parse(url));
            if (mimeType != null && !mimeType.isEmpty()) {
                solicitud.setMimeType(mimeType);
            }
            String cookie = CookieManager.getInstance().getCookie(url);
            if (cookie != null && !cookie.isEmpty()) {
                solicitud.addRequestHeader("Cookie", cookie);
            }
            if (userAgent != null && !userAgent.isEmpty()) {
                solicitud.addRequestHeader("User-Agent", userAgent);
            }
            solicitud.setTitle(nombre);
            solicitud.setDescription("Descarga de Escuela UAB");
            solicitud.setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            solicitud.setDestinationInExternalPublicDir(
                    Environment.DIRECTORY_DOWNLOADS, "EscuelaUAB/" + nombre);

            DownloadManager gestor =
                    (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
            if (gestor == null) {
                throw new IllegalStateException("DownloadManager no disponible");
            }
            gestor.enqueue(solicitud);
            Toast.makeText(this, "Descargando: " + nombre, Toast.LENGTH_LONG).show();
        } catch (Exception err) {
            Toast.makeText(this, "No se pudo descargar. Se abrirá en el navegador.",
                    Toast.LENGTH_LONG).show();
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
            } catch (Exception ignored) {
                // Sin navegador disponible.
            }
        }
    }

    private void cargarUrl(String url) {
        try {
            webView.loadUrl(url);
        } catch (Exception err) {
            mostrarPaginaError("La dirección no es válida: " + url);
        }
    }

    private String urlActual() {
        String actual = webView.getUrl();
        if (actual == null || actual.isEmpty()) {
            actual = prefs.getString(CLAVE_URL, URL_POR_DEFECTO);
        }
        return actual;
    }

    private String baseDelServidor() {
        try {
            URI uri = new URI(urlActual());
            if (uri.getHost() == null) {
                return null;
            }
            int puerto = uri.getPort();
            String base = uri.getScheme() + "://" + uri.getHost();
            if (puerto > 0) {
                base += ":" + puerto;
            }
            return base;
        } catch (Exception err) {
            return null;
        }
    }

    private String normalizarUrl(String texto) {
        String valor = texto == null ? "" : texto.trim();
        if (valor.isEmpty()) {
            return null;
        }
        if (!valor.startsWith("http://") && !valor.startsWith("https://")) {
            valor = "https://" + valor;
        }
        try {
            URI uri = new URI(valor);
            if (uri.getHost() == null || uri.getHost().isEmpty()) {
                return null;
            }
            String ruta = uri.getPath();
            if (ruta == null || ruta.isEmpty() || "/".equals(ruta)) {
                valor = valor.replaceAll("/+$", "") + "/escuela";
            }
            return valor;
        } catch (Exception err) {
            return null;
        }
    }

    private Set<String> hostsConfiables() {
        return new HashSet<>(prefs.getStringSet(CLAVE_HOSTS, new HashSet<>()));
    }

    private void recordarHost(String host) {
        Set<String> hosts = hostsConfiables();
        hosts.add(host);
        prefs.edit().putStringSet(CLAVE_HOSTS, hosts).apply();
    }

    private void mostrarDialogoServidor() {
        final EditText campo = new EditText(this);
        campo.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        campo.setText(prefs.getString(CLAVE_URL, URL_POR_DEFECTO));
        campo.setSelectAllOnFocus(true);
        campo.setSingleLine(true);

        final AlertDialog dialogo = new AlertDialog.Builder(this)
                .setTitle("Dirección del servidor")
                .setMessage("Escribe la IP de la PC que ejecuta la escuela. Ejemplo:\n"
                        + "https://192.168.1.50:5443/escuela\n\n"
                        + "La PC y el celular deben estar en la misma WiFi.")
                .setView(campo)
                .setPositiveButton("Guardar", null)
                .setNegativeButton("Cancelar", null)
                .setNeutralButton("Restaurar", (d, which) -> {
                    prefs.edit().remove(CLAVE_URL).apply();
                    cargarUrl(URL_POR_DEFECTO);
                })
                .create();

        dialogo.setOnShowListener(d -> dialogo.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(v -> {
                    String url = normalizarUrl(campo.getText().toString());
                    if (url == null) {
                        campo.setError("Escribe una dirección válida, por ejemplo 192.168.1.50:5443");
                        return;
                    }
                    prefs.edit().putString(CLAVE_URL, url).apply();
                    dialogo.dismiss();
                    cargarUrl(url);
                }));
        dialogo.show();
    }

    private void mostrarPaginaError(String detalle) {
        String html = "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
                + "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                + "<style>"
                + "body{font-family:sans-serif;background:#f4f6f5;color:#123;margin:0;padding:32px 22px;text-align:center}"
                + "h1{font-size:20px;color:#0b5d3b}"
                + "p{line-height:1.5;color:#40564b;white-space:pre-line}"
                + ".caja{background:#fff;border-radius:14px;padding:22px;max-width:420px;margin:0 auto;box-shadow:0 6px 20px rgba(0,0,0,.08)}"
                + "button{display:block;margin:14px auto 0;padding:14px 20px;border:0;border-radius:12px;"
                + "background:#0b5d3b;color:#fff;font-size:16px;width:100%;max-width:320px}"
                + "button.sec{background:#fff;color:#0b5d3b;border:2px solid #0b5d3b}"
                + "</style></head><body><div class=\"caja\">"
                + "<h1>Sin conexión con la escuela</h1>"
                + "<p>No se pudo abrir el panel en la PC.</p>"
                + "<p><b>" + escaparHtml(detalle) + "</b></p>"
                + "<p>Verifica que la PC esté encendida, que el servidor siga corriendo, "
                + "que el celular esté en la misma WiFi y que la IP sea la correcta.</p>"
                + "<button onclick=\"AndroidEscuela.recargar()\">Reintentar</button>"
                + "<button class=\"sec\" onclick=\"AndroidEscuela.cambiarServidor()\">Cambiar servidor</button>"
                + "</div></body></html>";
        webView.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null);
    }

    private String escaparHtml(String texto) {
        if (texto == null) {
            return "";
        }
        return texto.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;");
    }

    private class PuenteWeb {
        @JavascriptInterface
        public void recargar() {
            runOnUiThread(() -> {
                String url = prefs.getString(CLAVE_URL, URL_POR_DEFECTO);
                cargarUrl(url);
            });
        }

        @JavascriptInterface
        public void cambiarServidor() {
            runOnUiThread(MainActivity.this::mostrarDialogoServidor);
        }
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        menu.add(Menu.NONE, MENU_RECARGAR, Menu.NONE, "Recargar");
        menu.add(Menu.NONE, MENU_SERVIDOR, Menu.NONE, "Cambiar servidor");
        menu.add(Menu.NONE, MENU_CERTIFICADO, Menu.NONE, "Certificado de la escuela");
        menu.add(Menu.NONE, MENU_NAVEGADOR, Menu.NONE, "Abrir en el navegador");
        menu.add(Menu.NONE, MENU_ACERCA, Menu.NONE, "Acerca de");
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        int id = item.getItemId();
        if (id == MENU_RECARGAR) {
            webView.reload();
            return true;
        }
        if (id == MENU_SERVIDOR) {
            mostrarDialogoServidor();
            return true;
        }
        if (id == MENU_CERTIFICADO) {
            mostrarDialogoCertificado();
            return true;
        }
        if (id == MENU_NAVEGADOR) {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(urlActual())));
            } catch (Exception err) {
                Toast.makeText(this, "No hay navegador disponible.", Toast.LENGTH_SHORT).show();
            }
            return true;
        }
        if (id == MENU_ACERCA) {
            new AlertDialog.Builder(this)
                    .setTitle("Escuela UAB")
                    .setMessage("Cliente Android de la Escuela de Fútbol UAB.\n\n"
                            + "Los datos se guardan en la PC (Flask + SQLite). "
                            + "El celular solo se conecta por WiFi/LAN.\n\n"
                            + "Versión 1.0")
                    .setPositiveButton("Cerrar", null)
                    .show();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    private void mostrarDialogoCertificado() {
        String base = baseDelServidor();
        String mensaje = "Esta app ya confía en la CA local de la Escuela UAB "
                + "(incluida dentro de la APK).\n\n"
                + "Si además quieres instalar el certificado en el sistema (por ejemplo para "
                + "usar Chrome o la PWA), abre el enlace y sigue las instrucciones de Android.";
        AlertDialog.Builder constructor = new AlertDialog.Builder(this)
                .setTitle("Certificado de la escuela")
                .setMessage(mensaje)
                .setPositiveButton("Cerrar", null);
        if (base != null) {
            constructor.setNeutralButton("Abrir ca.crt", (d, which) -> {
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(base + "/ca.crt")));
                } catch (Exception err) {
                    Toast.makeText(this, "No hay navegador disponible.", Toast.LENGTH_SHORT).show();
                }
            });
        }
        constructor.show();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        boolean concedido = grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED;

        if (requestCode == CODIGO_CAMARA) {
            if (permisoPendiente != null) {
                if (concedido) {
                    permisoPendiente.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
                } else {
                    permisoPendiente.deny();
                    Toast.makeText(this, "Sin permiso de cámara no se puede escanear el QR. "
                            + "Puedes marcar la asistencia manualmente.", Toast.LENGTH_LONG).show();
                }
                permisoPendiente = null;
            }
            return;
        }

        if (requestCode == CODIGO_ALMACENAMIENTO) {
            if (concedido && descargaUrl != null) {
                iniciarDescarga(descargaUrl, descargaUserAgent, descargaNombre, descargaMime);
            } else {
                Toast.makeText(this, "Sin permiso de almacenamiento no se puede guardar el respaldo.",
                        Toast.LENGTH_LONG).show();
            }
            descargaUrl = null;
            return;
        }
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
            return;
        }
        long ahora = System.currentTimeMillis();
        if (ahora - ultimoAtras < 2000) {
            super.onBackPressed();
            return;
        }
        ultimoAtras = ahora;
        Toast.makeText(this, "Presiona atrás otra vez para salir", Toast.LENGTH_SHORT).show();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }

    @Override
    protected void onPause() {
        super.onPause();
        webView.onPause();
        CookieManager.getInstance().flush();
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.loadUrl("about:blank");
            webView.removeAllViews();
            webView.destroy();
        }
        super.onDestroy();
    }
}
