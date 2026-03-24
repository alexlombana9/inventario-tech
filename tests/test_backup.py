"""Tests para el modulo de backup."""
import models


class TestBackupPage:
    def test_page_admin(self, admin_client):
        resp = admin_client.get("/backup")
        assert resp.status_code == 200

    def test_page_vendedor_no_puede(self, vendedor_client):
        resp = vendedor_client.get("/backup", follow_redirects=False)
        assert resp.status_code in (303, 403)


class TestDescargarBackup:
    def test_descargar_genera_sql(self, admin_client, db, sample_producto):
        resp = admin_client.get("/backup/descargar")
        assert resp.status_code == 200
        assert resp.headers.get("content-type") in (
            "application/sql",
            "application/sql; charset=utf-8",
        )
        content = resp.content.decode("utf-8")
        assert "TechStock Backup" in content or "pg_dump" in content.lower() or "INSERT" in content


class TestCrearBackupLocal:
    def test_crear_backup_local(self, admin_client):
        resp = admin_client.post("/backup/crear", follow_redirects=False)
        assert resp.status_code == 303
        assert "backup" in resp.headers["location"].lower()
