"""Locks the OpenAPI contract so it cannot silently rot.

PR #59 made the generated spec truthful: a bearer security scheme,
per-route `security`, and declared 400/401/403/404 error responses
referencing the real `ErrorOut` model. Without this test, a future
careless edit could quietly regress the spec back to the
under-documented state — the contract a client builds against would
lie again, with nothing failing. These assertions make that
impossible: the contract is self-defending.

The app's OpenAPI document is generated synchronously; no DB or Redis
is needed, so these are fast pure-spec assertions (no fixtures).
"""

from app.main import app


def _spec() -> dict:
    return app.openapi()


# --- security scheme ---------------------------------------------------

def test_bearer_security_scheme_is_declared() -> None:
    spec = _spec()
    schemes = spec.get("components", {}).get("securitySchemes", {})
    assert "HTTPBearer" in schemes, schemes
    assert schemes["HTTPBearer"]["type"] == "http"
    assert schemes["HTTPBearer"]["scheme"] == "bearer"


def test_protected_route_requires_bearer() -> None:
    # /v1/auth/me is bearer-only; it must advertise the requirement
    op = _spec()["paths"]["/v1/auth/me"]["get"]
    assert op.get("security") == [{"HTTPBearer": []}], op.get("security")


def test_public_routes_do_not_falsely_require_auth() -> None:
    # register/login take no token — the spec must NOT claim they do,
    # and must NOT declare an auth-401 they never return
    spec = _spec()
    for path in ("/v1/auth/register", "/v1/auth/login"):
        op = spec["paths"][path]["post"]
        assert not op.get("security"), (path, op.get("security"))
    # register returns 400 (email taken), never a 401
    reg = spec["paths"]["/v1/auth/register"]["post"]["responses"]
    assert "401" not in reg, reg.keys()
    assert "400" in reg, reg.keys()


# --- declared error responses -----------------------------------------

def _resp_codes(spec: dict, path: str, method: str) -> set[str]:
    return set(spec["paths"][path][method]["responses"].keys())


def test_routes_declare_their_real_error_responses() -> None:
    spec = _spec()
    expectations = {
        ("/v1/auth/login", "post"): {"401"},
        ("/v1/auth/refresh", "post"): {"401"},
        ("/v1/workspaces/{workspace_id}/members", "post"):
            {"401", "404", "409"},
        ("/v1/workspaces/{workspace_id}/audit", "get"):
            {"401", "404", "400"},
        ("/v1/workspaces/{workspace_id}/activity", "get"):
            {"401", "404", "400"},
        ("/v1/workspaces/{workspace_id}/tasks", "post"):
            {"401", "404"},
        ("/v1/workspaces/{workspace_id}/tasks/{task_id}", "delete"):
            {"401", "404"},
        ("/v1/workspaces/{workspace_id}/tasks/{task_id}/comments",
         "get"): {"401", "404", "400"},
        ("/v1/workspaces/{workspace_id}/tasks/{task_id}/comments/"
         "{comment_id}", "patch"): {"401", "403", "404"},
    }
    for (path, method), required in expectations.items():
        got = _resp_codes(spec, path, method)
        missing = required - got
        assert not missing, f"{method.upper()} {path} missing {missing} (has {got})"


def test_declared_errors_reference_the_error_model() -> None:
    # the documented error responses must point at the real ErrorOut
    # schema, not an undocumented blob
    spec = _spec()
    op = spec["paths"]["/v1/workspaces/{workspace_id}/tasks/{task_id}"
                        "/comments/{comment_id}"]["patch"]
    for code in ("401", "403", "404"):
        schema = op["responses"][code]["content"]["application/json"]["schema"]
        assert schema.get("$ref", "").endswith("/ErrorOut"), (code, schema)


def test_error_model_shape_matches_the_wire_contract() -> None:
    # ErrorOut documents the REAL doubled shape: {detail:{detail,code}}
    schemas = _spec()["components"]["schemas"]
    assert "ErrorOut" in schemas
    assert "ErrorDetail" in schemas
    detail = schemas["ErrorDetail"]["properties"]
    assert set(detail.keys()) == {"detail", "code"}, detail.keys()
