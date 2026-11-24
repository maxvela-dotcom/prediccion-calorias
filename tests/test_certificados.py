# -*- coding: utf-8 -*-
"""
Pruebas de la CA local (src/certificados.py).

La CA debe conservarse cuando solo cambia la IP de la PC: el `ca.crt`
instalado en los celulares y el que va dentro de la APK siguen siendo
válidos; únicamente se regenera el certificado del servidor.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import certificados
from cryptography import x509


class TestCertificados(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self._originales = {
            "BASE_CERTS": certificados.BASE_CERTS,
            "RUTA_CA": certificados.RUTA_CA,
            "RUTA_CLAVE_CA": certificados.RUTA_CLAVE_CA,
            "RUTA_CERT_SERVIDOR": certificados.RUTA_CERT_SERVIDOR,
            "RUTA_CLAVE_SERVIDOR": certificados.RUTA_CLAVE_SERVIDOR,
        }
        certificados.BASE_CERTS = base
        certificados.RUTA_CA = os.path.join(base, "ca.crt")
        certificados.RUTA_CLAVE_CA = os.path.join(base, "ca.key")
        certificados.RUTA_CERT_SERVIDOR = os.path.join(base, "servidor.crt")
        certificados.RUTA_CLAVE_SERVIDOR = os.path.join(base, "servidor.key")

    def tearDown(self):
        for nombre, valor in self._originales.items():
            setattr(certificados, nombre, valor)
        self._tmp.cleanup()

    def _leer(self, ruta):
        with open(ruta, "rb") as archivo:
            return archivo.read()

    def test_reutiliza_ca_al_cambiar_ip(self):
        certificados.generar_certificados(["192.168.1.10", "localhost"])
        ca_antes = self._leer(certificados.RUTA_CA)
        servidor_antes = self._leer(certificados.RUTA_CERT_SERVIDOR)

        certificados.generar_certificados(["192.168.1.99", "localhost"])
        ca_despues = self._leer(certificados.RUTA_CA)
        servidor_despues = self._leer(certificados.RUTA_CERT_SERVIDOR)

        self.assertEqual(ca_antes, ca_despues)
        self.assertNotEqual(servidor_antes, servidor_despues)

        ca = x509.load_pem_x509_certificate(ca_despues)
        servidor = x509.load_pem_x509_certificate(servidor_despues)
        servidor.verify_directly_issued_by(ca)

        san = servidor.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value
        ips = {str(valor) for valor in san.get_values_for_type(x509.IPAddress)}
        self.assertIn("192.168.1.99", ips)
        self.assertNotIn("192.168.1.10", ips)

        # Extensiones estándar que exigen los clientes TLS estrictos.
        servidor.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier)
        servidor.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
        ca.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)

    def test_regenerar_ca_explicito(self):
        certificados.generar_certificados(["192.168.1.10"])
        ca_antes = self._leer(certificados.RUTA_CA)

        certificados.generar_certificados(["192.168.1.10"], regenerar_ca=True)
        ca_despues = self._leer(certificados.RUTA_CA)

        self.assertNotEqual(ca_antes, ca_despues)

    def test_cubre_varias_ips_y_las_reporta(self):
        # La PC puede tener varias IPs (WiFi, cable, hotspot): el certificado
        # debe servir en todas para funcionar en cualquier red.
        ips = ["192.168.1.10", "10.0.0.25", "172.20.5.7"]
        certificados.generar_certificados(ips + ["localhost"])

        cubiertos = certificados.hosts_cubiertos()
        for ip in ips:
            self.assertIn(ip, cubiertos)
        self.assertIn("localhost", cubiertos)

    def test_asegurar_agrega_ip_nueva_sin_cambiar_ca(self):
        # Simula cambiar de WiFi: aparece una IP nueva y la CA se conserva,
        # así el certificado instalado en los celulares sigue siendo válido.
        certificados.asegurar_certificados(["192.168.1.10", "localhost"])
        ca_antes = self._leer(certificados.RUTA_CA)

        certificados.asegurar_certificados(["192.168.1.10", "10.0.0.25", "localhost"])

        self.assertEqual(ca_antes, self._leer(certificados.RUTA_CA))
        self.assertIn("10.0.0.25", certificados.hosts_cubiertos())


if __name__ == "__main__":
    unittest.main()
