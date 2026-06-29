"""Tests for errors.py: code-to-exception mapping and exit-code contract.

These tests defend the public contract that scripts depend on:
- which backend `code` slug maps to which exception class
- which exit code each exception class reports
"""
from __future__ import annotations

import pytest

from taskflow_cli import errors


# --- Exit code constants ---------------------------------------------------

@pytest.mark.parametrize(
    "name, expected",
    [
        ("EXIT_OK", 0),
        ("EXIT_GENERIC", 1),
        ("EXIT_USAGE", 2),
        ("EXIT_AUTH", 10),
        ("EXIT_NOT_FOUND", 11),
        ("EXIT_FORBIDDEN", 12),
        ("EXIT_CONFLICT", 13),
        ("EXIT_NETWORK", 14),
        ("EXIT_BAD_REQUEST", 15),
        ("EXIT_SERVER", 16),
    ],
)
def test_exit_code_values(name, expected):
    """The exit-code contract is documented in README; these values are stable."""
    assert getattr(errors, name) == expected


# --- ApiError base class ---------------------------------------------------

def test_api_error_carries_message_and_http_status():
    """ApiError takes message positionally and http_status as a keyword."""
    e = errors.ApiError("boom", http_status=500)
    assert str(e) == "boom"
    assert e.message == "boom"
    assert e.http_status == 500


def test_api_error_code_default_is_none_at_base():
    """Subclasses override `code` as a class attribute; the base default is None."""
    e = errors.ApiError("boom")
    assert e.code is None


def test_subclass_code_is_class_attribute_not_constructor_arg():
    """A subclass exposes its code without the caller passing it in."""
    e = errors.InvalidCredentials("wrong password")
    assert e.code == "invalid_credentials"

def test_api_error_default_exit_code_is_generic():
    e = errors.ApiError("boom")
    assert e.exit_code == errors.EXIT_GENERIC


# --- Per-code exception classes --------------------------------------------

@pytest.mark.parametrize(
    "exc_class, expected_exit",
    [
        (errors.InvalidCredentials, errors.EXIT_AUTH),
        (errors.InvalidToken, errors.EXIT_AUTH),
        (errors.EmailUnavailable, errors.EXIT_CONFLICT),
        (errors.UserNotFound, errors.EXIT_NOT_FOUND),
        (errors.MemberNotFound, errors.EXIT_NOT_FOUND),
        (errors.AlreadyMember, errors.EXIT_CONFLICT),
        (errors.CannotRemoveOwner, errors.EXIT_CONFLICT),
        (errors.TaskNotFound, errors.EXIT_NOT_FOUND),
        (errors.CommentNotFound, errors.EXIT_NOT_FOUND),
        (errors.NotCommentAuthor, errors.EXIT_FORBIDDEN),
        (errors.InvalidCursor, errors.EXIT_BAD_REQUEST),
        (errors.ValidationError, errors.EXIT_BAD_REQUEST),
        (errors.NetworkError, errors.EXIT_NETWORK),
        (errors.ServerError, errors.EXIT_SERVER),
    ],
)
def test_exception_class_has_correct_exit_code(exc_class, expected_exit):
    """Each typed exception carries the right exit code at the class level."""
    inst = exc_class("test message")
    assert inst.exit_code == expected_exit


# --- The CODE_TO_EXCEPTION map ---------------------------------------------

@pytest.mark.parametrize(
    "code, expected_class",
    [
        ("invalid_credentials", errors.InvalidCredentials),
        ("invalid_token", errors.InvalidToken),
        ("email_unavailable", errors.EmailUnavailable),
        ("user_not_found", errors.UserNotFound),
        ("member_not_found", errors.MemberNotFound),
        ("already_member", errors.AlreadyMember),
        ("cannot_remove_owner", errors.CannotRemoveOwner),
        ("task_not_found", errors.TaskNotFound),
        ("comment_not_found", errors.CommentNotFound),
        ("not_comment_author", errors.NotCommentAuthor),
        ("invalid_cursor", errors.InvalidCursor),
    ],
)
def test_code_to_exception_mapping(code, expected_class):
    """The map from backend code slug to exception class is the integration contract."""
    assert errors.CODE_TO_EXCEPTION[code] is expected_class


def test_code_to_exception_has_no_unexpected_entries():
    """Defensive: surfaces accidental additions for review."""
    expected_keys = {
        "invalid_credentials", "invalid_token", "email_unavailable",
        "user_not_found", "member_not_found", "already_member",
        "cannot_remove_owner", "task_not_found", "comment_not_found",
        "not_comment_author", "invalid_cursor",
    }
    assert set(errors.CODE_TO_EXCEPTION.keys()) == expected_keys
