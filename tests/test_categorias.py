"""Tests para el modulo de categorias (CRUD)."""
import models


class TestListaCategorias:
    def test_lista_vacia(self, admin_client):
        resp = admin_client.get("/categorias")
        assert resp.status_code == 200

    def test_lista_con_datos(self, admin_client, sample_categoria):
        resp = admin_client.get("/categorias")
        assert resp.status_code == 200
        assert "Electronicos" in resp.text

    def test_buscar_categoria(self, admin_client, sample_categoria):
        """Cubre linea 17: filtro buscar en lista de categorias."""
        resp = admin_client.get("/categorias?buscar=Electro")
        assert resp.status_code == 200
        assert "Electronicos" in resp.text

    def test_buscar_sin_resultados(self, admin_client, sample_categoria):
        """Cubre linea 17: busqueda que no encuentra resultados."""
        resp = admin_client.get("/categorias?buscar=NoExisteEstaCategoria")
        assert resp.status_code == 200


class TestCrearCategoria:
    def test_crear_ok(self, admin_client, db):
        resp = admin_client.post("/categorias/nueva", data={
            "nombre": "Accesorios",
            "descripcion": "Accesorios varios",
        }, follow_redirects=False)
        assert resp.status_code == 303
        cat = db.query(models.Categoria).filter_by(nombre="Accesorios").first()
        assert cat is not None
        assert cat.descripcion == "Accesorios varios"

    def test_crear_duplicada(self, admin_client, sample_categoria):
        resp = admin_client.post("/categorias/nueva", data={
            "nombre": "Electronicos",
            "descripcion": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_crear_sin_nombre(self, admin_client):
        resp = admin_client.post("/categorias/nueva", data={
            "descripcion": "Sin nombre",
        })
        assert resp.status_code == 422


class TestEditarCategoria:
    def test_editar_ok(self, admin_client, db, sample_categoria):
        resp = admin_client.post(f"/categorias/{sample_categoria.id}/editar", data={
            "nombre": "Electronicos Actualizados",
            "descripcion": "Nueva descripcion",
        }, follow_redirects=False)
        assert resp.status_code == 303
        db.refresh(sample_categoria)
        assert sample_categoria.nombre == "Electronicos Actualizados"

    def test_editar_inexistente(self, admin_client):
        resp = admin_client.post("/categorias/9999/editar", data={
            "nombre": "Nada",
            "descripcion": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_editar_nombre_duplicado(self, admin_client, db, sample_categoria):
        otra = models.Categoria(nombre="Ropa", descripcion="")
        db.add(otra)
        db.commit()

        resp = admin_client.post(f"/categorias/{otra.id}/editar", data={
            "nombre": "Electronicos",
            "descripcion": "",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()


class TestEliminarCategoria:
    def test_eliminar_sin_productos(self, admin_client, db, sample_categoria):
        resp = admin_client.post(
            f"/categorias/{sample_categoria.id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db.refresh(sample_categoria)
        assert sample_categoria.activo is False

    def test_eliminar_con_productos(self, admin_client, sample_producto):
        cat_id = sample_producto.categoria_id
        resp = admin_client.post(
            f"/categorias/{cat_id}/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "error" in resp.headers["location"].lower()

    def test_eliminar_inexistente(self, admin_client):
        resp = admin_client.post(
            "/categorias/9999/eliminar",
            follow_redirects=False,
        )
        assert resp.status_code == 303
