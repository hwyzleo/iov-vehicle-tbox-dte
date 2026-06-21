"""Tests for UDS security access adapters."""
from __future__ import annotations

import pytest

from dte.uds.security import (
    CallableAdapter,
    FixedKeyAdapter,
    SecurityAccessAdapter,
    SecurityAccessError,
    XORAdapter,
    create_adapter,
)


class TestSecurityAccessAdapterABC:
    """Tests for the abstract SecurityAccessAdapter base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SecurityAccessAdapter()

    def test_subclass_must_implement_compute_key(self):
        class IncompleteAdapter(SecurityAccessAdapter):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteAdapter()

    def test_subclass_with_compute_key_works(self):
        class CompleteAdapter(SecurityAccessAdapter):
            def compute_key(self, seed: bytes, level: int) -> bytes:
                return seed

        adapter = CompleteAdapter()
        assert adapter.compute_key(b"\x01\x02", 1) == b"\x01\x02"


class TestFixedKeyAdapter:
    """Tests for FixedKeyAdapter."""

    def test_returns_fixed_key_regardless_of_seed(self):
        adapter = FixedKeyAdapter(key=b"\xAA\xBB\xCC")
        assert adapter.compute_key(b"\x00\x00\x00", 1) == b"\xAA\xBB\xCC"
        assert adapter.compute_key(b"\xFF\xFF\xFF", 1) == b"\xAA\xBB\xCC"

    def test_returns_fixed_key_regardless_of_level(self):
        adapter = FixedKeyAdapter(key=b"\xAA\xBB")
        assert adapter.compute_key(b"\x01\x02", 1) == b"\xAA\xBB"
        assert adapter.compute_key(b"\x01\x02", 3) == b"\xAA\xBB"

    def test_key_property(self):
        key = b"\x11\x22\x33"
        adapter = FixedKeyAdapter(key=key)
        assert adapter.key == key

    def test_empty_key(self):
        adapter = FixedKeyAdapter(key=b"")
        assert adapter.compute_key(b"\x01", 1) == b""


class TestXORAdapter:
    """Tests for XORAdapter."""

    def test_xor_single_byte(self):
        adapter = XORAdapter(key=b"\xFF")
        result = adapter.compute_key(b"\x0F", 1)
        assert result == b"\xF0"

    def test_xor_multi_byte(self):
        adapter = XORAdapter(key=b"\xAA\x55")
        result = adapter.compute_key(b"\x55\xAA", 1)
        assert result == b"\xFF\xFF"

    def test_xor_key_longer_than_seed(self):
        adapter = XORAdapter(key=b"\xAA\x55\xFF")
        result = adapter.compute_key(b"\x01\x02", 1)
        assert result == b"\xAB\x57"

    def test_xor_seed_longer_than_key(self):
        adapter = XORAdapter(key=b"\xFF")
        result = adapter.compute_key(b"\x01\x02\x03", 1)
        assert result == b"\xFE\xFD\xFC"

    def test_xor_with_zero_key(self):
        adapter = XORAdapter(key=b"\x00\x00")
        result = adapter.compute_key(b"\xAB\xCD", 1)
        assert result == b"\xAB\xCD"

    def test_xor_regardless_of_level(self):
        adapter = XORAdapter(key=b"\xFF")
        assert adapter.compute_key(b"\x01", 1) == adapter.compute_key(b"\x01", 3)


class TestCallableAdapter:
    """Tests for CallableAdapter."""

    def test_callable_adapter_with_function(self):
        def my_algo(seed: bytes, level: int) -> bytes:
            return bytes(b + 1 for b in seed)

        adapter = CallableAdapter(fn=my_algo)
        assert adapter.compute_key(b"\x00\x01", 1) == b"\x01\x02"

    def test_callable_adapter_receives_level(self):
        received_levels = []

        def my_algo(seed: bytes, level: int) -> bytes:
            received_levels.append(level)
            return seed

        adapter = CallableAdapter(fn=my_algo)
        adapter.compute_key(b"\x01", 1)
        adapter.compute_key(b"\x01", 3)
        assert received_levels == [1, 3]

    def test_callable_adapter_with_lambda(self):
        adapter = CallableAdapter(fn=lambda seed, level: bytes(reversed(seed)))
        assert adapter.compute_key(b"\x01\x02\x03", 1) == b"\x03\x02\x01"

    def test_callable_adapter_callable_property(self):
        def fn(seed: bytes, level: int) -> bytes:
            return seed

        adapter = CallableAdapter(fn=fn)
        assert adapter.callable is fn


class TestSecurityAccessError:
    """Tests for SecurityAccessError exception."""

    def test_is_exception(self):
        assert issubclass(SecurityAccessError, Exception)

    def test_can_be_raised_with_message(self):
        with pytest.raises(SecurityAccessError, match="test error"):
            raise SecurityAccessError("test error")

    def test_can_be_caught_as_exception(self):
        with pytest.raises(Exception):
            raise SecurityAccessError("test")


class TestCreateAdapter:
    """Tests for create_adapter factory function."""

    def test_create_fixed_adapter(self):
        adapter = create_adapter("fixed", key=b"\xAA\xBB")
        assert isinstance(adapter, FixedKeyAdapter)
        assert adapter.compute_key(b"\x00", 1) == b"\xAA\xBB"

    def test_create_xor_adapter(self):
        adapter = create_adapter("xor", key=b"\xFF")
        assert isinstance(adapter, XORAdapter)
        assert adapter.compute_key(b"\x0F", 1) == b"\xF0"

    def test_create_callable_adapter(self):
        def fn(seed: bytes, level: int) -> bytes:
            return bytes(reversed(seed))

        adapter = create_adapter("callable", fn=fn)
        assert isinstance(adapter, CallableAdapter)
        assert adapter.compute_key(b"\x01\x02\x03", 1) == b"\x03\x02\x01"

    def test_create_callable_adapter_missing_fn(self):
        with pytest.raises(ValueError, match="fn parameter is required"):
            create_adapter("callable")

    def test_create_invalid_adapter_type(self):
        with pytest.raises(ValueError, match="Invalid adapter_type"):
            create_adapter("invalid")
