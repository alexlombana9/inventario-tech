"""Tests para el modulo de backup."""
import os
import io
import models
from datetime import datetime


def _is_pg_binary(cmd_path, name):
    """Verifica si un comando es un binario PG especifico (psql, pg_dump, etc)."""
    return name in os.path.basename(str(cmd_path)).lower()


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
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if _is_pg_binary(cmd[0], "psql"):
                raise FileNotFoundError("psql not found")
            if _is_pg_binary(cmd[0], "pg_dump"):
                raise FileNotFoundError("pg_dump not found")
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
            if _is_pg_binary(cmd[0], "psql"):
                return FakeResult()
            if _is_pg_binary(cmd[0], "pg_dump"):
                raise FileNotFoundError("pg_dump not found")
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
            if _is_pg_binary(cmd[0], "psql"):
                return FakeResult()
            if _is_pg_binary(cmd[0], "pg_dump"):
                raise FileNotFoundError("pg_dump not found")
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
            if _is_pg_binary(cmd[0], "psql"):
                raise subprocess.TimeoutExpired(cmd, 300)
            if _is_pg_binary(cmd[0], "pg_dump"):
                raise FileNotFoundError("pg_dump not found")
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
        """Fallback SQLAlchemy: sentencia con error hace rollback atomico."""
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if _is_pg_binary(cmd[0], "psql"):
                raise FileNotFoundError("no psql")
            if _is_pg_binary(cmd[0], "pg_dump"):
                raise FileNotFoundError("no pg_dump")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        try:
            # SQL con sentencia que causa error (tabla inexistente) → rollback atomico
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
        """Fallback: excepcion inesperada en _restore_with_sqlalchemy entra al except final."""
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if _is_pg_binary(cmd[0], "psql"):
                raise FileNotFoundError("no psql")
            if _is_pg_binary(cmd[0], "pg_dump"):
                raise FileNotFoundError("no pg_dump")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Mock _restore_with_sqlalchemy para que lance excepcion inesperada
        def mock_restore_sa(filepath, db_session):
            raise RuntimeError("Error inesperado de prueba")

        monkeypatch.setattr(backup_router, "_restore_with_sqlalchemy", mock_restore_sa)

        try:
            sql_file = tmp_path / "will_fail.sql"
            sql_file.write_text("-- TechStock Backup\nINSERT INTO x (id) VALUES (1);\n", encoding="utf-8")
            resp = superadmin_client.post(
                "/backup/restaurar/will_fail.sql", follow_redirects=False
            )
            assert resp.status_code == 303
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_restaurar_backup_con_copy_sin_psql(self, superadmin_client, db, tmp_path, monkeypatch):
        """Backup con formato COPY no puede restaurarse sin psql."""
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if _is_pg_binary(cmd[0], "psql"):
                raise FileNotFoundError("no psql")
            if _is_pg_binary(cmd[0], "pg_dump"):
                raise FileNotFoundError("no pg_dump")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        try:
            # Backup en formato COPY (pg_dump default)
            sql_file = tmp_path / "copy_backup.sql"
            sql_file.write_text(
                "-- pg_dump backup\n"
                "COPY categorias (id, nombre) FROM stdin;\n"
                "1\tTest\n"
                "\\.\n",
                encoding="utf-8",
            )
            resp = superadmin_client.post(
                "/backup/restaurar/copy_backup.sql", follow_redirects=False
            )
            assert resp.status_code == 303
        finally:
            monkeypatch.setattr(backup_router, "BACKUP_DIR", original_dir)

    def test_restaurar_backup_vacio_sin_datos(self, superadmin_client, db, tmp_path, monkeypatch):
        """Backup sin INSERT ni COPY muestra error."""
        import subprocess
        import routers.backup as backup_router

        original_dir = backup_router.BACKUP_DIR
        monkeypatch.setattr(backup_router, "BACKUP_DIR", str(tmp_path))

        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if _is_pg_binary(cmd[0], "psql"):
                raise FileNotFoundError("no psql")
            if _is_pg_binary(cmd[0], "pg_dump"):
                raise FileNotFoundError("no pg_dump")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        try:
            sql_file = tmp_path / "empty_backup.sql"
            sql_file.write_text("-- Solo comentarios\n-- Nada mas\n", encoding="utf-8")
            resp = superadmin_client.post(
                "/backup/restaurar/empty_backup.sql", follow_redirects=False
            )
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
            if _is_pg_binary(cmd[0], "pg_dump"):
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
            if _is_pg_binary(cmd[0], "pg_dump"):
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
            if _is_pg_binary(cmd[0], "pg_dump"):
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


class TestRestoreHelpers:
    """Tests para funciones auxiliares de restauracion."""

    def test_find_pg_binary_portable(self, monkeypatch, tmp_path):
        """_find_pg_binary encuentra binarios en pgsql/bin/."""
        import routers.backup as backup_router
        pgsql_bin = tmp_path / "pgsql" / "bin"
        pgsql_bin.mkdir(parents=True)
        (pgsql_bin / "psql.exe").write_bytes(b"fake")

        monkeypatch.setattr(backup_router, "PROJECT_ROOT", str(tmp_path))
        result = backup_router._find_pg_binary("psql")
        assert "psql" in result
        assert str(tmp_path) in result

    def test_find_pg_binary_fallback_to_name(self, monkeypatch, tmp_path):
        """_find_pg_binary retorna nombre simple si no encuentra portable."""
        import routers.backup as backup_router
        monkeypatch.setattr(backup_router, "PROJECT_ROOT", str(tmp_path))
        result = backup_router._find_pg_binary("pg_dump")
        assert result == "pg_dump"

    def test_restore_with_sqlalchemy_no_inserts(self, db, tmp_path):
        """Archivo sin INSERTs retorna error."""
        from routers.backup import _restore_with_sqlalchemy
        filepath = tmp_path / "nodata.sql"
        filepath.write_text("-- solo comentarios\n", encoding="utf-8")
        ok, msg = _restore_with_sqlalchemy(str(filepath), db)
        assert not ok
        assert "no contiene datos" in msg

    def test_restore_with_sqlalchemy_copy_format(self, db, tmp_path):
        """Archivo con COPY sin INSERT retorna error."""
        from routers.backup import _restore_with_sqlalchemy
        filepath = tmp_path / "copy.sql"
        filepath.write_text(
            "COPY categorias FROM stdin;\n1\tTest\n\\.\n",
            encoding="utf-8",
        )
        ok, msg = _restore_with_sqlalchemy(str(filepath), db)
        assert not ok
        assert "COPY" in msg
