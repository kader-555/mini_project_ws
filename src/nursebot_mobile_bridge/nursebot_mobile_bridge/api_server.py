#!/usr/bin/env python3
import asyncio
import json

import rclpy
from rclpy.executors import MultiThreadedExecutor

from nursebot_mobile_bridge.ros_bridge import MobileBridgeNode


class AppState:
    def __init__(self):
        self.bridge = None
        self.executor = None
        self.spin_task = None


state = AppState()


def create_app():
    try:
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.middleware.cors import CORSMiddleware
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "FastAPI is not installed. Install it with:\n"
            "  python3 -m pip install --user fastapi 'uvicorn[standard]'\n"
            "then run:\n"
            "  ros2 run nursebot_mobile_bridge api_server"
        ) from exc

    app = FastAPI(title="nursebot_mobile_bridge")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def start_ros():
        if state.bridge is not None:
            return

        rclpy.init()
        state.bridge = MobileBridgeNode()
        state.executor = MultiThreadedExecutor()
        state.executor.add_node(state.bridge)

    def stop_ros():
        if state.executor is not None and state.bridge is not None:
            state.executor.remove_node(state.bridge)
            state.bridge.destroy_node()
            state.bridge = None
        if rclpy.ok():
            rclpy.shutdown()

    @app.on_event("startup")
    async def on_startup():
        start_ros()

        async def spin_ros():
            while rclpy.ok():
                state.executor.spin_once(timeout_sec=0.1)
                await asyncio.sleep(0.01)

        state.spin_task = asyncio.create_task(spin_ros())

    @app.on_event("shutdown")
    async def on_shutdown():
        if state.spin_task is not None:
            state.spin_task.cancel()
        stop_ros()

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/status")
    def status():
        if state.bridge is None:
            return {"ok": False, "error": "ROS bridge not started"}
        return state.bridge.get_status() if hasattr(state.bridge, "get_status") else {"ok": True}

    # ======THE NEW WEBSOCKET CHANGES======
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket structure:
        1. client connects
        2. server accepts
        3. server sends an initial state message
        4. server keeps sending updates
        5. server receives commands from the client
        6. close on disconnect
        """
        await websocket.accept()

        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "connected",
                        "message": "WebSocket connected",
                    }
                )
            )

            while True:
                if state.bridge is not None and hasattr(state.bridge, "get_status"):
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "status",
                                "data": state.bridge.get_status(),
                            }
                        )
                    )

                try:
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=0.2)
                    data = json.loads(message)

                    if data.get("type") == "goal":
                        patient_id = data.get("patient_id")
                        result = state.bridge.send_patient_goal(patient_id)
                        await websocket.send_text(json.dumps({"type": "goal_ack", "result": result}))

                    elif data.get("type") == "cancel":
                        result = state.bridge.cancel_goal()
                        await websocket.send_text(json.dumps({"type": "cancel_ack", "result": result}))

                except asyncio.TimeoutError:
                    pass

        except WebSocketDisconnect:
            return

    return app


def main():
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
