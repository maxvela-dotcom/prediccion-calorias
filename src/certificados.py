# -*- coding: utf-8 -*-
"""
Certificados HTTPS locales — Willys_IA.

Genera una CA propia y un certificado de servidor con las IP de la red local.
Así la app se puede abrir por HTTPS (cámara + service worker/PWA) sin depender
de OpenSSL ni de un dominio público.

Los archivos quedan en src/certs/:
- ca.crt       → se instala una vez en cada celular (autoridad de confianza)
- ca.key       → clave privada de la CA (no compartir)
- servidor.crt → certificado del servidor
- servidor.key → clave privada del servidor
"""

import datetime
import ipaddress
import os
import socket
from typing import Dict, Iterable, List, Optional, Set

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

BASE_CERTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "certs")
RUTA_CA = os.path.join(BASE_CERTS, "ca.crt")
RUTA_CLAVE_CA = os.path.join(BASE_CERTS, "ca.key")
RUTA_CERT_SERVIDOR = os.path.join(BASE_CERTS, "servidor.crt")
RUTA_CLAVE_SERVIDOR = os.path.join(BASE_CERTS, "servidor.key")

_DIAS_VALIDEZ_CA = 3650
_DIAS_VALIDEZ_SERVIDOR = 825  # límite práctico de navegadores móviles
_DIAS_RENOVACION = 30


def _ahora() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _escribir(ruta: str, datos: bytes) -> None:
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "wb") as archivo:
        archivo.write(datos)


def _clave_rsa():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem_clave(clave) -> bytes:
    return clave.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _pem_certificado(certificado) -> bytes:
    return certificado.public_bytes(serialization.Encoding.PEM)


def _nombres_para(hosts: Optional[Iterable[str]]) -> Dict[str, Set]:
    """Reúne DNS e IPs que debe cubrir el certificado."""
    dns: Set[str] = {"localhost"}
    ips: Set[str] = {"127.0.0.1", "::1"}

    try:
        nombre_equipo = socket.gethostname().strip().lower()
        if nombre_equipo:
            dns.add(nombre_equipo)
    except OSError:
        pass

    for host in hosts or []:
        valor = (host or "").strip()
        if not valor:
            continue
        try:
            ips.add(str(ipaddress.ip_address(valor)))
        except ValueError:
            dns.add(valor.lower())

    return {"dns": dns, "ips": ips}


def _subject_alternative_name(hosts: Optional[Iterable[str]]) -> x509.SubjectAlternativeName:
    nombres = _nombres_para(hosts)
    entradas: List[x509.GeneralName] = [
        x509.DNSName(nombre) for nombre in sorted(nombres["dns"])
    ]
    entradas.extend(
        x509.IPAddress(ipaddress.ip_address(ip)) for ip in sorted(nombres["ips"])
    )
    return x509.SubjectAlternativeName(entradas)


def _cargar_certificado(ruta: str):
    try:
        with open(ruta, "rb") as archivo:
            return x509.load_pem_x509_certificate(archivo.read())
    except (OSError, ValueError):
        return None


def _cargar_clave(ruta: str):
    try:
        with open(ruta, "rb") as archivo:
            return serialization.load_pem_private_key(archivo.read(), password=None)
    except (OSError, ValueError, TypeError):
        return None


def _ca_existente():
    """Devuelve (clave, certificado) de la CA actual si sigue siendo válida."""
    clave_ca = _cargar_clave(RUTA_CLAVE_CA)
    certificado_ca = _cargar_certificado(RUTA_CA)
    if clave_ca is None or certificado_ca is None:
        return None

    ahora = _ahora()
    if certificado_ca.not_valid_after_utc - datetime.timedelta(days=_DIAS_RENOVACION) <= ahora:
        return None
    if certificado_ca.not_valid_before_utc > ahora:
        return None

    # La clave privada debe corresponder al certificado.
    try:
        if clave_ca.public_key().public_numbers() != certificado_ca.public_key().public_numbers():
            return None
    except AttributeError:
        return None

    # Los certificados nuevos incluyen SubjectKeyIdentifier; si falta, se
    # regenera la CA una vez para que los clientes estrictos validen la cadena.
    try:
        certificado_ca.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
    except x509.ExtensionNotFound:
        return None

    return clave_ca, certificado_ca


def _certificado_utilizable(hosts: Optional[Iterable[str]]) -> bool:
    """Comprueba vigencia, emisor y que el certificado cubra la IP actual."""
    certificado = _cargar_certificado(RUTA_CERT_SERVIDOR)
    if certificado is None:
        return False
    if not os.path.exists(RUTA_CLAVE_SERVIDOR):
        return False

    ca = _ca_existente()
    if ca is None:
        return False
    _, certificado_ca = ca

    # El certificado del servidor debe haber sido firmado por esta misma CA.
    try:
        certificado.verify_directly_issued_by(certificado_ca)
    except (ValueError, TypeError, AttributeError):
        return False

    # Autoridad emisora explícita: requerida por OpenSSL estricto.
    try:
        certificado.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier)
    except x509.ExtensionNotFound:
        return False

    ahora = _ahora()
    if certificado.not_valid_after_utc - datetime.timedelta(days=_DIAS_RENOVACION) <= ahora:
        return False

    try:
        san = certificado.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value
    except x509.ExtensionNotFound:
        return False

    dns_cert = {str(valor).lower() for valor in san.get_values_for_type(x509.DNSName)}
    ip_cert = {str(valor) for valor in san.get_values_for_type(x509.IPAddress)}
    requeridos = _nombres_para(hosts)

    return requeridos["dns"].issubset(dns_cert) and requeridos["ips"].issubset(ip_cert)


def _crear_ca(ahora: datetime.datetime):
    """Crea una nueva autoridad certificadora local."""
    clave_ca = _clave_rsa()
    nombre_ca = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BO"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Escuela de Futbol UAB"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Escuela de Futbol UAB - CA local"),
        ]
    )
    certificado_ca = (
        x509.CertificateBuilder()
        .subject_name(nombre_ca)
        .issuer_name(nombre_ca)
        .public_key(clave_ca.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - datetime.timedelta(days=1))
        .not_valid_after(ahora + datetime.timedelta(days=_DIAS_VALIDEZ_CA))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(clave_ca.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(clave_ca.public_key()),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(clave_ca, hashes.SHA256())
    )
    return clave_ca, certificado_ca


def generar_certificados(
    hosts: Optional[Iterable[str]] = None, regenerar_ca: bool = False
) -> Dict[str, str]:
    """Crea el certificado del servidor reutilizando la CA local.

    La CA solo se regenera si no existe, venció o si se pide explícitamente.
    Así el `ca.crt` instalado en los celulares (y el incluido en el APK) sigue
    siendo válido aunque cambie la IP de la PC.
    """
    os.makedirs(BASE_CERTS, exist_ok=True)
    ahora = _ahora()

    # 1) Autoridad certificadora local: reutilizar la existente.
    ca = None if regenerar_ca else _ca_existente()
    if ca is None:
        clave_ca, certificado_ca = _crear_ca(ahora)
        _escribir(RUTA_CA, _pem_certificado(certificado_ca))
        _escribir(RUTA_CLAVE_CA, _pem_clave(clave_ca))
    else:
        clave_ca, certificado_ca = ca
    nombre_ca = certificado_ca.subject

    # 2) Certificado del servidor firmado por la CA.
    clave_servidor = _clave_rsa()
    nombre_servidor = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BO"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Escuela de Futbol UAB"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Escuela de Futbol UAB - servidor"),
        ]
    )
    certificado_servidor = (
        x509.CertificateBuilder()
        .subject_name(nombre_servidor)
        .issuer_name(nombre_ca)
        .public_key(clave_servidor.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - datetime.timedelta(days=1))
        .not_valid_after(ahora + datetime.timedelta(days=_DIAS_VALIDEZ_SERVIDOR))
        .add_extension(_subject_alternative_name(hosts), critical=False)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(clave_servidor.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(clave_ca.public_key()),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(clave_ca, hashes.SHA256())
    )

    _escribir(RUTA_CERT_SERVIDOR, _pem_certificado(certificado_servidor))
    _escribir(RUTA_CLAVE_SERVIDOR, _pem_clave(clave_servidor))

    return rutas_certificados()


def asegurar_certificados(hosts: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """Genera los certificados solo si faltan, vencieron o cambió la IP local."""
    if _certificado_utilizable(hosts):
        return rutas_certificados()
    return generar_certificados(hosts)


def hosts_cubiertos() -> Set[str]:
    """Nombres e IPs que ya incluye el certificado actual del servidor.

    Sirve para detectar cambios de red: si la PC recibe una IP nueva (otra
    WiFi), esa IP no estará en el conjunto y habrá que regenerar el
    certificado del servidor (la CA se conserva).
    """
    certificado = _cargar_certificado(RUTA_CERT_SERVIDOR)
    if certificado is None:
        return set()
    try:
        san = certificado.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value
    except x509.ExtensionNotFound:
        return set()

    cubiertos = {str(valor).lower() for valor in san.get_values_for_type(x509.DNSName)}
    cubiertos |= {str(valor) for valor in san.get_values_for_type(x509.IPAddress)}
    return cubiertos


def rutas_certificados() -> Dict[str, str]:
    return {
        "ca": RUTA_CA,
        "cert": RUTA_CERT_SERVIDOR,
        "key": RUTA_CLAVE_SERVIDOR,
    }
