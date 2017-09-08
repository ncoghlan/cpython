"""Additional signal safety tests for "with" and "async with"
"""

from test.support import cpython_only, verbose
from _testcapi import install_error_injection_hook
import asyncio
import dis
import sys
import threading
import unittest

class InjectedException(Exception):
    """Exception injected into a running frame via a trace function"""
    pass

def raise_after_offset(target_function, target_offset):
    """Sets a trace function to inject an exception into given function

    Relies on the ability to request that a trace function be called for
    every executed opcode, not just every line
    """
    target_code = target_function.__code__
    def inject_exception():
        exc = InjectedException(f"Failing after {target_offset}")
        raise exc
    # This installs a trace hook that's implemented in C, and hence won't
    # trigger any of the per-bytecode processing in the eval loop
    # This means it can register the pending call that raises the exception and
    # the pending call won't be processed until after the trace hook returns
    install_error_injection_hook(target_code, target_offset, inject_exception)

# TODO: Add a test case that ensures raise_after_offset is working
# properly (otherwise there's a risk the tests will pass due to the
# exception not being injected properly)

@cpython_only
class CheckFunctionSignalSafety(unittest.TestCase):
    """Ensure with statements are signal-safe.

    Signal safety means that, regardless of when external signals (e.g.
    KeyboardInterrupt) are received, if __enter__ succeeds, __exit__ will
    be called.

    See https://bugs.python.org/issue29988 for more details
    """

    def setUp(self):
        old_trace = sys.gettrace()
        self.addCleanup(sys.settrace, old_trace)
        sys.settrace(None)

    def assert_lock_released(self, test_lock, target_offset, traced_operation):
        just_acquired = test_lock.acquire(blocking=False)
        # Either we just acquired the lock, or the test didn't release it
        test_lock.release()
        if not just_acquired:
            msg = ("Context manager entered without exit due to "
                  f"exception injected at offset {target_offset} in:\n"
                  f"{dis.Bytecode(traced_operation).dis()}")
            self.fail(msg)

    def _check_CM_exits_correctly(self, traced_function):
        # Must use a signal-safe CM, otherwise __exit__ will start
        # but then fail to actually run as the pending call gets processed
        test_lock = threading.Lock()
        target_offset = -1
        traced_code = dis.Bytecode(traced_function)
        for instruction in traced_code:
            if instruction.opname == "RETURN_VALUE":
                return_offset = instruction.offset
                break
        while target_offset < return_offset:
            target_offset += 1
            raise_after_offset(traced_function, target_offset)
            try:
                traced_function(test_lock)
            except InjectedException:
                # key invariant: if we entered the CM, we exited it
                self.assert_lock_released(test_lock, target_offset, traced_function)
            else:
                msg = (f"Exception wasn't raised @{target_offset} in:\n"
                       f"{dis.Bytecode(traced_function).dis()}")
                self.fail(msg)

    def test_with_statement_completed(self):
        def traced_function(test_cm):
            with test_cm:
                1 + 1
            return # Make implicit final return explicit
        self._check_CM_exits_correctly(traced_function)

    def test_with_statement_exited_via_return(self):
        def traced_function(test_cm):
            with test_cm:
                1 + 1
                return
            return # Make implicit final return explicit
        self._check_CM_exits_correctly(traced_function)

    def test_with_statement_exited_via_continue(self):
        def traced_function(test_cm):
            for i in range(1):
                with test_cm:
                    1 + 1
                    continue
            return # Make implicit final return explicit
        self._check_CM_exits_correctly(traced_function)

    def test_with_statement_exited_via_break(self):
        def traced_function(test_cm):
            while True:
                with test_cm:
                    1 + 1
                    break
            return # Make implicit final return explicit
        self._check_CM_exits_correctly(traced_function)

    def test_with_statement_exited_via_raise(self):
        def traced_function(test_cm):
            try:
                with test_cm:
                    1 + 1
                    1/0
            except ZeroDivisionError:
                pass
            return # Make implicit final return explicit
        self._check_CM_exits_correctly(traced_function)

@cpython_only
class CheckCoroutineSignalSafety(unittest.TestCase):
    """Ensure async with statements are signal-safe.

    Signal safety means that, regardless of when external signals (e.g.
    KeyboardInterrupt) are received, if __aenter__ succeeeds, __aexit__ will
    be called *and* the resulting awaitable will be awaited.

    See https://bugs.python.org/issue29988 for more details
    """

    def _test_asynchronous_cm(self):
        # NOTE: this can't work, since asyncio is written in Python, and hence
        # will always process pending calls at some point during the evaluation
        # of __aenter__ and __aexit__
        #
        # So to handle that case, we need to some way to tell the event loop
        # to convert pending call processing into calls to
        # asyncio.get_event_loop().call_soon() instead of processing them
        # immediately
        class AsyncTrackingCM():
            def __init__(self):
                self.enter_without_exit = None
            async def __aenter__(self):
                self.enter_without_exit = True
            async def __aexit__(self, *args):
                self.enter_without_exit = False
        tracking_cm = AsyncTrackingCM()
        async def traced_coroutine():
            async with tracking_cm:
                1 + 1
            return
        target_offset = -1
        max_offset = len(traced_coroutine.__code__.co_code) - 2
        loop = asyncio.get_event_loop()
        while target_offset < max_offset:
            target_offset += 1
            raise_after_offset(traced_coroutine, target_offset)
            try:
                loop.run_until_complete(traced_coroutine())
            except InjectedException:
                # key invariant: if we entered the CM, we exited it
                self.assertFalse(tracking_cm.enter_without_exit)
            else:
                self.fail(f"Exception wasn't raised @{target_offset}")


if __name__ == '__main__':
    unittest.main()
