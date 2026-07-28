import asyncio

from src.api.runtime import GenerationGate, QueueFullError, QueueWaitTimeoutError


def test_generation_gate_bounds_active_and_pending():
    async def scenario():
        gate = GenerationGate(max_active=1, max_pending=1, wait_seconds=0.03)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def holder():
            async with gate.slot():
                entered.set()
                await release.wait()

        task = asyncio.create_task(holder())
        await entered.wait()

        async def waiter():
            async with gate.slot():
                return True

        waiting = asyncio.create_task(waiter())
        await asyncio.sleep(0)
        assert gate.snapshot()["pending"] == 1

        try:
            async with gate.slot():
                raise AssertionError("queue-full request must not enter")
        except QueueFullError:
            pass

        try:
            await waiting
            raise AssertionError("waiting request should time out")
        except QueueWaitTimeoutError:
            pass

        release.set()
        await task
        assert gate.snapshot()["active"] == 0
        assert gate.snapshot()["pending"] == 0

    asyncio.run(scenario())


def test_generation_gate_accepts_three_active_and_six_pending():
    async def scenario():
        gate = GenerationGate(max_active=3, max_pending=6, wait_seconds=1)
        release = asyncio.Event()
        active_ready = asyncio.Event()
        active_count = 0

        async def holder():
            nonlocal active_count
            async with gate.slot():
                active_count += 1
                if active_count == 3:
                    active_ready.set()
                await release.wait()

        holders = [asyncio.create_task(holder()) for _ in range(3)]
        await active_ready.wait()

        async def queued_request():
            async with gate.slot():
                return True

        waiting = [asyncio.create_task(queued_request()) for _ in range(6)]
        for _ in range(100):
            if gate.snapshot()["pending"] == 6:
                break
            await asyncio.sleep(0.001)

        assert gate.snapshot() == {
            "active": 3,
            "pending": 6,
            "max_active": 3,
            "max_pending": 6,
        }

        try:
            async with gate.slot():
                raise AssertionError("the tenth generation request must be rejected")
        except QueueFullError:
            pass

        release.set()
        assert all(await asyncio.gather(*waiting))
        await asyncio.gather(*holders)
        assert gate.snapshot()["active"] == 0
        assert gate.snapshot()["pending"] == 0

    asyncio.run(scenario())
