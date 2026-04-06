#!/usr/bin/env python3
import rclpy 
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from action_msgs.msg import GoalStatusArray
from nursebot_mobile_bridge.patient import patient
import tf_transformations  
from nursebot_interfaces.msg import StdMsgs


class MobileBridgeNode(Node):
    def __init__(self):
        super().__init__('mobile_bridge_node')
        self.goal_pose_publisher = self.create_publisher(
            PoseStamped ,
            'goal_pose',
            10
            )
        self.patient_id_sub = self.create_subscription(StdMsgs, 'patient_id', self.patient_id_callback, 10)
        self.goal = None 
        self.last_patient_id = None
        self.last_status = None
        self.get_logger().info('Mobile Bridge Node has been started.')
        self.status_sub = self.create_subscription(
            GoalStatusArray,
            '/navigate_to_pose/_action/status',
            self.status_callback,
            10
            )
        
    def patient_id_callback(self, msg):
        patient_id = msg.patient_id
        self.send_patient_goal(patient_id)

    def status_callback(self, msg):
        if len(msg.status_list) > 0:
            status = msg.status_list[-1].status
            self.last_status = status

            if status == 4:  # STATUS_SUCCEEDED
                self.get_logger().info("Goal reached! Robot stopped.")  
                self.goal = None

    # ======THE NEW WEBSOCKET CHANGES======
    def get_status(self):
        return {
            "patient_id": self.last_patient_id,
            "status": self.last_status,
            "goal": self.goal,
        }

    def send_patient_goal(self, patient_id):
        if patient_id in patient:
            self.goal = patient[patient_id]
            self.last_patient_id = patient_id
            self.publish_goal_pose()
            self.get_logger().info(f"Received patient ID: {patient_id}. Goal set to: {self.goal}")
            return {"ok": True, "patient_id": patient_id, "goal": self.goal}

        self.get_logger().warn(f"Received unknown patient ID: {patient_id}. No goal set.")
        return {"ok": False, "error": "unknown patient_id", "patient_id": patient_id}

    def cancel_goal(self):
        self.goal = None
        self.last_patient_id = None
        self.get_logger().info("Goal cancelled from the web API.")
        return {"ok": True}

    # This function will publish the goal pose to the 'goal_pose' topic
    def publish_goal_pose(self ):
        msg = PoseStamped()
        if self.goal is None:
            return
        x,y,theta = self.goal
        msg.header.frame_id = 'map'
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = 0.0 

        
        q_x, q_y, q_z, q_w = tf_transformations.quaternion_from_euler(0.0, 0.0, theta)
        msg.pose.orientation.x = q_x 
        msg.pose.orientation.y = q_y 
        msg.pose.orientation.z = q_z 
        msg.pose.orientation.w = q_w 

        self.goal_pose_publisher.publish(msg)
        self.get_logger().info(f"Published goal pose: ({x}, {y}, {theta})")

def main(args=None):
    rclpy.init(args=args)
    mobile_bridge_node = MobileBridgeNode()
    
    rclpy.spin(mobile_bridge_node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
