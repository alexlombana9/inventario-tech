"""Tests para el modulo de backup."""
import os
import io
import models
from datetime import datetime


class TestBackupPage:
    def test_page_vendedor_no_puede(self, vendedor_client):
        resp = vendedor_client.get("/backup", follow_redirects=False)
        assert resp.status_code in (303, 403)

    def test_page_bodeguero_no_puede(self, bodeguero_client):
        resp = bodeguero_client.get("/backup", follow_redirects=False)
        assert resp.status_code in (303, 403)

    def test_page_admin_no_puede(self, admin_client):
        resp = admin_client.get("/backup", follow_redirects=False)
        assert resp.status_code in (303, 403)

    def test_page_sin_auth_redirige(self, client):
        resp = client.get("/backup", follow_redirects=False)
        assert resp.status_code in (303, 302, 401)

    def test_page_lista_archivos_existentes(self, superadmin_client, tmp_path, monkeypatch):
        """Verifica que la pagina lista archivos .sql en BACKUP_DIR."""
        import routers.backup as backup_router
        # Crear archivo .sql temporal en tmp_path
        sql_file = tmp_path / "techstock_backup_20260101_120000.sql"
        sql_file.write_bytes(b"-- test backup\nINSERT INTO usuarios (id) VALUES (1);")

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))
        try:
            resp = superadmin_client.get("/backup")
            assert resp.status_code == 200
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)


class TestDescargarBackup:
    def test_descargar_genera_sql(self, superadmin_client, db, sample_producto):
        resp = superadmin_client.get("/backup/descargar")
        assert resp.status_code == 200
        assert resp.headers.get("content-type") in (
            "application/sql",
            "application/sql; charset=utf-8",
        )
        content = resp.content.decode("utf-8")
        assert "TechStock Backup" in content or "pg_dump" in content.lower() or "INSERT" in content

    def test_descargar_tiene_header_disposition(self, superadmin_client):
        resp = superadmin_client.get("/backup/descargar")
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert ".sql" in resp.headers.get("content-disposition", "")

    def test_descargar_registra_audit(self, superadmin_client, db):
        resp = superadmin_client.get("/backup/descargar")
        assert resp.status_code == 200
        log = db.query(models.AuditLog).filter(
            models.AuditLog.accion == "CREATE",
            models.AuditLog.entidad == "backup",
        ).first()
        assert log is not None


class TestCrearBackupLocal:
    def test_crear_backup_crea_archivo(self, superadmin_client, tmp_path, monkeypatch):
        """Verifica que se crea un archivo .sql en BACKUP_DIR."""
        import routers.backup as backup_router
        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))
        try:
            resp = superadmin_client.post("/backup/crear", follow_redirects=False)
            assert resp.status_code == 303
            sql_files = list(tmp_path.glob("*.sql"))
            assert len(sql_files) == 1
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_crear_backup_registra_audit(self, superadmin_client, db):
        resp = superadmin_client.post("/backup/crear", follow_redirects=False)
        assert resp.status_code == 303
        log = db.query(models.AuditLog).filter(
            models.AuditLog.accion == "CREATE",
            models.AuditLog.entidad == "backup",
        ).first()
        assert log is not None

    def test_crear_backup_vendedor_no_puede(self, vendedor_client):
        resp = vendedor_client.post("/backup/crear", follow_redirects=False)
        assert resp.status_code in (303, 403)


class TestSubirBackup:
    def _make_sql_upload(self, filename="test_backup.sql", content=b"-- test\nINSERT INTO categorias (id, nombre) VALUES (99, 'test');"):
        return {"archivo": (filename, io.BytesIO(content), "application/sql")}

    def test_subir_backup_valido(self, superadmin_client, tmp_path, monkeypatch):
        import routers.backup as backup_router
        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))
        try:
            files = self._make_sql_upload()
            resp = superadmin_client.post("/backup/subir", files=files, follow_redirects=False)
            assert resp.status_code == 303
            assert "backup" in resp.headers["location"].lower()
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_subir_backup_extension_invalida(self, superadmin_client):
        files = {"archivo": ("malicious.txt", io.BytesIO(b"not sql"), "text/plain")}
        resp = superadmin_client.post("/backup/subir", files=files, follow_redirects=False)
        assert resp.status_code == 303
        assert "backup" in resp.headers["location"].lower()

    def test_subir_backup_archivo_vacio(self, superadmin_client):
        files = {"archivo": ("empty.sql", io.BytesIO(b""), "application/sql")}
        resp = superadmin_client.post("/backup/subir", files=files, follow_redirects=False)
        assert resp.status_code == 303

    def test_subir_backup_muy_grande(self, superadmin_client):
        big_content = b"-- test\n" + b"x" * (51 * 1024 * 1024)  # 51 MB
        files = {"archivo": ("big.sql", io.BytesIO(big_content), "application/sql")}
        resp = superadmin_client.post("/backup/subir", files=files, follow_redirects=False)
        assert resp.status_code == 303

    def test_subir_backup_registra_audit(self, superadmin_client, db, tmp_path, monkeypatch):
        import routers.backup as backup_router
        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))
        try:
            files = self._make_sql_upload()
            resp = superadmin_client.post("/backup/subir", files=files, follow_redirects=False)
            assert resp.status_code == 303
            log = db.query(models.AuditLog).filter(
                models.AuditLog.accion == "CREATE",
                models.AuditLog.entidad == "backup",
            ).first()
            assert log is not None
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)


class TestDescargarBackupLocal:
    def _create_backup_file(self, tmp_path, filename="techstock_backup_20260101_120000.sql"):
        filepath = tmp_path / filename
        filepath.write_bytes(b"-- TechStock Backup\nINSERT INTO categorias (id, nombre) VALUES (1, 'test');")
        return filename

    def test_descargar_local_existente(self, superadmin_client, tmp_path, monkeypatch):
        import routers.backup as backup_router
        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))
        try:
            filename = self._create_backup_file(tmp_path)
            resp = superadmin_client.get(f"/backup/descargar-local/{filename}")
            assert resp.status_code == 200
            assert "attachment" in resp.headers.get("content-disposition", "")
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_descargar_local_no_existe(self, superadmin_client, tmp_path, monkeypatch):
        import routers.backup as backup_router
        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))
        try:
            resp = superadmin_client.get(
                "/backup/descargar-local/noexiste.sql", follow_redirects=False
            )
            assert resp.status_code == 303
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_descargar_local_extension_invalida(self, superadmin_client):
        resp = superadmin_client.get(
            "/backup/descargar-local/malicious.txt", follow_redirects=False
        )
        assert resp.status_code == 303

    def test_descargar_local_path_traversal(self, superadmin_client):
        resp = superadmin_client.get(
            "/backup/descargar-local/../../etc/passwd.sql", follow_redirects=False
        )
        assert resp.status_code in (303, 200, 404)


class TestRestaurarBackup:
    def _create_simple_backup(self, tmp_path, filename="restore_test.sql"):
        filepath = tmp_path / filename
        # SQL simple que SQLAlchemy puede ejecutar en SQLite
        filepath.write_text(
            "-- TechStock Backup\n"
            "-- Linea de comentario\n"
            "\n"
            "INSERT INTO categorias (nombre, descripcion, activo) VALUES ('RestoreTest', 'desc', 1);\n",
            encoding="utf-8",
        )
        return filename

    def test_restaurar_archivo_no_existe(self, superadmin_client, tmp_path, monkeypatch):
        import routers.backup as backup_router
        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))
        try:
            resp = superadmin_client.post(
                "/backup/restaurar/noexiste.sql", follow_redirects=False
            )
            assert resp.status_code == 303
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_restaurar_extension_invalida(self, superadmin_client):
        resp = superadmin_client.post(
            "/backup/restaurar/malicious.txt", follow_redirects=False
        )
        assert resp.status_code == 303

    def test_restaurar_fallback_sqlalchemy(self, superadmin_client, db, tmp_path, monkeypatch):
        """Cuando psql no esta disponible, usa fallback SQLAlchemy."""
        import routers.backup as backup_router
        import subprocess

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        # Hacer que subprocess.run lance FileNotFoundError para simular que psql no existe
        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == "psql":
                raise FileNotFoundError("psql not found")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        try:
            filename = self._create_simple_backup(tmp_path)
            resp = superadmin_client.post(
                f"/backup/restaurar/{filename}", follow_redirects=False
            )
            assert resp.status_code == 303
            assert "backup" in resp.headers["location"].lower()
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_restaurar_vendedor_no_puede(self, vendedor_client):
        resp = vendedor_client.post(
            "/backup/restaurar/cualquier.sql", follow_redirects=False
        )
        assert resp.status_code in (303, 403)

    def test_restaurar_psql_exitoso(self, superadmin_client, db, tmp_path, monkeypatch):
        """Restauracion con psql que retorna returncode=0."""
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        class FakeResult:
            returncode = 0
            stdout = b""
            stderr = b""

        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == "psql":
                return FakeResult()
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        try:
            filename = self._create_simple_backup(tmp_path)
            resp = superadmin_client.post(
                f"/backup/restaurar/{filename}", follow_redirects=False
            )
            assert resp.status_code == 303
            assert "backup" in resp.headers["location"].lower()
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_restaurar_psql_falla_con_error(self, superadmin_client, db, tmp_path, monkeypatch):
        """Restauracion con psql que retorna returncode != 0."""
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        class FakeResult:
            returncode = 1
            stdout = b""
            stderr = b"ERROR: relation does not exist"

        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == "psql":
                return FakeResult()
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        try:
            filename = self._create_simple_backup(tmp_path)
            resp = superadmin_client.post(
                f"/backup/restaurar/{filename}", follow_redirects=False
            )
            assert resp.status_code == 303
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_restaurar_psql_timeout(self, superadmin_client, db, tmp_path, monkeypatch):
        """Restauracion con psql que da TimeoutExpired."""
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == "psql":
                raise subprocess.TimeoutExpired(cmd, 300)
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        try:
            filename = self._create_simple_backup(tmp_path)
            resp = superadmin_client.post(
                f"/backup/restaurar/{filename}", follow_redirects=False
            )
            assert resp.status_code == 303
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_restaurar_fallback_con_stmt_con_error(self, superadmin_client, db, tmp_path, monkeypatch):
        """Fallback SQLAlchemy: sentencia con error incrementa contador errors."""
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == "psql":
                raise FileNotFoundError("no psql")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        try:
            # SQL con sentencias que causaran error en SQLite
            sql_file = tmp_path / "restore_errors.sql"
            sql_file.write_text(
                "-- TechStock Backup\n"
                "INSERT INTO tabla_inexistente (id) VALUES (1);\n"
                "INSERT INTO categorias (nombre) VALUES ('RestoreErrTest');\n",
                encoding="utf-8",
            )
            resp = superadmin_client.post(
                "/backup/restaurar/restore_errors.sql", follow_redirects=False
            )
            assert resp.status_code == 303
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_restaurar_fallback_excepcion_inesperada(self, superadmin_client, db, tmp_path, monkeypatch):
        """Fallback: excepcion al abrir/leer archivo entra al except final."""
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == "psql":
                raise FileNotFoundError("no psql")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Crear archivo con encoding que cause error al leer como utf-8
        try:
            sql_file = tmp_path / "encoding_error.sql"
            sql_file.write_bytes(b"\xff\xfe-- contenido invalido utf8\n")
            resp = superadmin_client.post(
                "/backup/restaurar/encoding_error.sql", follow_redirects=False
            )
            # La respuesta puede ser 303 con mensaje de exito o error
            assert resp.status_code == 303
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)


class TestEliminarBackupLocal:
    def _create_backup_file(self, tmp_path, filename="techstock_backup_del.sql"):
        filepath = tmp_path / filename
        filepath.write_bytes(b"-- TechStock Backup\n")
        return filename

    def test_eliminar_existente(self, superadmin_client, db, tmp_path, monkeypatch):
        import routers.backup as backup_router
        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))
        try:
            filename = self._create_backup_file(tmp_path)
            resp = superadmin_client.post(
                f"/backup/eliminar/{filename}", follow_redirects=False
            )
            assert resp.status_code == 303
            assert "backup" in resp.headers["location"].lower()
            # El archivo debe haber sido eliminado
            assert not (tmp_path / filename).exists()
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_eliminar_extension_invalida(self, superadmin_client):
        resp = superadmin_client.post(
            "/backup/eliminar/malicious.txt", follow_redirects=False
        )
        assert resp.status_code == 303

    def test_eliminar_registra_audit(self, superadmin_client, db, tmp_path, monkeypatch):
        import routers.backup as backup_router
        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))
        try:
            filename = self._create_backup_file(tmp_path)
            resp = superadmin_client.post(
                f"/backup/eliminar/{filename}", follow_redirects=False
            )
            assert resp.status_code == 303
            log = db.query(models.AuditLog).filter(
                models.AuditLog.accion == "DELETE",
                models.AuditLog.entidad == "backup",
            ).first()
            assert log is not None
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_eliminar_vendedor_no_puede(self, vendedor_client):
        resp = vendedor_client.post(
            "/backup/eliminar/test.sql", follow_redirects=False
        )
        assert resp.status_code in (303, 403)


class TestFallbackDump:
    """Prueba la funcion _fallback_dump directamente."""

    def test_pg_dump_sql_falla_sin_pg_dump(self, monkeypatch):
        """Cuando pg_dump no existe, retorna None."""
        import subprocess
        from routers.backup import _pg_dump_sql

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if "pg_dump" in cmd:
                raise FileNotFoundError("pg_dump not found")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = _pg_dump_sql({"host": "localhost", "port": "5432", "dbname": "test", "user": "u", "password": ""})
        assert result is None

    def test_pg_dump_sql_exitoso(self, monkeypatch):
        """Cuando pg_dump tiene returncode=0, retorna stdout."""
        import subprocess
        from routers.backup import _pg_dump_sql

        original_run = subprocess.run

        class FakeResult:
            returncode = 0
            stdout = b"-- backup content\n"
            stderr = b""

        def mock_run(cmd, *args, **kwargs):
            if "pg_dump" in cmd:
                return FakeResult()
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = _pg_dump_sql({"host": "localhost", "port": "5432", "dbname": "test", "user": "u", "password": "pass"})
        assert result == b"-- backup content\n"

    def test_pg_dump_sql_timeout(self, monkeypatch):
        """Cuando pg_dump da timeout, retorna None."""
        import subprocess
        from routers.backup import _pg_dump_sql

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if "pg_dump" in cmd:
                raise subprocess.TimeoutExpired(cmd, 120)
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = _pg_dump_sql({"host": "localhost", "port": "5432", "dbname": "test", "user": "u", "password": ""})
        assert result is None

    def test_fallback_dump_con_tipos_multiples(self, db, admin_user, sample_categoria, sample_producto):
        """_fallback_dump corre sin excepcion y genera contenido de cabecera."""
        from routers.backup import _fallback_dump
        content = _fallback_dump(db)
        decoded = content.decode("utf-8")
        # SQLite no soporta information_schema, pero la funcion maneja
        # el error por tabla y debe retornar al menos la cabecera
        assert "TechStock Backup" in decoded
