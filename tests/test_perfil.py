"""Tests para el modulo de perfil de usuario."""
import models
from auth import verify_password


class TestVerPerfil:
    def test_pagina_perfil(self, admin_client):
        resp = admin_client.get("/perfil")
        assert resp.status_code == 200

    def test_pagina_perfil_vendedor(self, vendedor_client):
        resp = vendedor_client.get("/perfil")
        assert resp.status_code == 200


class TestActualizarPerfil:
    def test_actualizar_nombre(self, admin_client, db, admin_user):
        resp = admin_client.post("/perfil", data={
            "nombre_completo": "Admin Renombrado",
            "email": "admin@nuevo.com",
            "telefono": "3001234567",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(admin_user)
        assert admin_user.nombre_completo == "Admin Renombrado"
        assert admin_user.email == "admin@nuevo.com"
        assert admin_user.telefono == "3001234567"

    def test_actualizar_solo_email(self, admin_client, db, admin_user):
        resp = admin_client.post("/perfil", data={
            "nombre_completo": admin_user.nombre_completo,
            "email": "solo_email@test.com",
            "telefono": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(admin_user)
        assert admin_user.email == "solo_email@test.com"

    def test_nombre_vacio_rechazado(self, admin_client, db, admin_user):
        nombre_original = admin_user.nombre_completo
        resp = admin_client.post("/perfil", data={
            "nombre_completo": "   ",
            "email": "",
            "telefono": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(admin_user)
        assert admin_user.nombre_completo == nombre_original

    def test_actualizar_genera_auditoria(self, admin_client, db):
        admin_client.post("/perfil", data={
            "nombre_completo": "Con Auditoria",
            "email": "",
            "telefono": "",
        }, follow_redirects=False)
        log = db.query(models.AuditLog).filter(
            models.AuditLog.entidad == "perfil",
            models.AuditLog.accion == "UPDATE",
        ).first()
        assert log is not None


class TestCambiarPassword:
    def test_cambiar_password_ok(self, admin_client, db, admin_user):
        resp = admin_client.post("/perfil/password", data={
            "password_actual": "admin12345",
            "password_nueva": "NuevaPass123",
            "password_confirmar": "NuevaPass123",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(admin_user)
        assert verify_password("NuevaPass123", admin_user.password_hash)

    def test_password_actual_incorrecta(self, admin_client, db, admin_user):
        old_hash = admin_user.password_hash
        resp = admin_client.post("/perfil/password", data={
            "password_actual": "IncorrectaPass1",
            "password_nueva": "NuevaPass123",
            "password_confirmar": "NuevaPass123",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(admin_user)
        assert admin_user.password_hash == old_hash

    def test_passwords_no_coinciden(self, admin_client, db, admin_user):
        old_hash = admin_user.password_hash
        resp = admin_client.post("/perfil/password", data={
            "password_actual": "admin12345",
            "password_nueva": "NuevaPass123",
            "password_confirmar": "OtraPass456",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(admin_user)
        assert admin_user.password_hash == old_hash

    def test_password_muy_corta(self, admin_client, db, admin_user):
        old_hash = admin_user.password_hash
        resp = admin_client.post("/perfil/password", data={
            "password_actual": "admin12345",
            "password_nueva": "short",
            "password_confirmar": "short",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(admin_user)
        assert admin_user.password_hash == old_hash


class TestEliminarFoto:
    def test_eliminar_foto_sin_foto(self, admin_client):
        """Eliminar foto cuando no hay foto no debe fallar."""
        resp = admin_client.post("/perfil/foto/eliminar", follow_redirects=False)
        assert resp.status_code == 303

    def test_eliminar_foto_con_foto(self, admin_client, db, admin_user, tmp_path, monkeypatch):
        """Simular foto existente y eliminarla (archivo en disco)."""
        import routers.perfil as perfil_module
        monkeypatch.setattr(perfil_module, "UPLOAD_DIR", str(tmp_path))

        # Crear archivo real en disco
        foto_file = tmp_path / "foto_test.jpg"
        foto_file.write_bytes(b"foto_data")

        user = db.query(models.Usuario).filter(models.Usuario.id == admin_user.id).first()
        user.foto = "foto_test.jpg"
        db.commit()

        resp = admin_client.post("/perfil/foto/eliminar", follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(admin_user)
        assert admin_user.foto == ""
        assert not foto_file.exists()  # Line 122: archivo eliminado


class TestSubirFoto:
    def test_subir_foto_extension_invalida(self, admin_client):
        """Lines 70-73: Formato no permitido rechaza con 303."""
        import io
        resp = admin_client.post(
            "/perfil/foto",
            files={"foto": ("archivo.txt", io.BytesIO(b"contenido"), "text/plain")},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_subir_foto_muy_grande(self, admin_client):
        """Lines 77-79: Imagen mayor a 2MB es rechazada."""
        import io
        contenido_grande = b"x" * (2 * 1024 * 1024 + 1)
        resp = admin_client.post(
            "/perfil/foto",
            files={"foto": ("imagen.jpg", io.BytesIO(contenido_grande), "image/jpeg")},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_subir_foto_valida(self, admin_client, db, admin_user, tmp_path, monkeypatch):
        """Lines 81-107: Foto valida se guarda correctamente."""
        import io
        import routers.perfil as perfil_module
        monkeypatch.setattr(perfil_module, "UPLOAD_DIR", str(tmp_path))

        resp = admin_client.post(
            "/perfil/foto",
            files={"foto": ("avatar.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(admin_user)
        assert admin_user.foto is not None and admin_user.foto != ""

    def test_subir_foto_reemplaza_anterior(self, admin_client, db, admin_user, tmp_path, monkeypatch):
        """Lines 88-91: Foto anterior se elimina al subir una nueva."""
        import io
        import routers.perfil as perfil_module
        monkeypatch.setattr(perfil_module, "UPLOAD_DIR", str(tmp_path))

        # Crear archivo de foto previa en el tmp_path
        foto_previa = tmp_path / "foto_vieja.jpg"
        foto_previa.write_bytes(b"vieja")

        user = db.query(models.Usuario).filter(models.Usuario.id == admin_user.id).first()
        user.foto = "foto_vieja.jpg"
        db.commit()

        resp = admin_client.post(
            "/perfil/foto",
            files={"foto": ("nueva.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        # El archivo viejo ya no debe existir
        assert not foto_previa.exists()

    def test_eliminar_foto_genera_auditoria(self, admin_client, db, admin_user):
        """Line 122: Eliminar foto registra entrada de auditoria."""
        user = db.query(models.Usuario).filter(models.Usuario.id == admin_user.id).first()
        user.foto = "foto_audit.jpg"
        db.commit()

        admin_client.post("/perfil/foto/eliminar", follow_redirects=False)

        log = db.query(models.AuditLog).filter(
            models.AuditLog.entidad == "perfil",
            models.AuditLog.accion == "UPDATE",
        ).first()
        assert log is not None
