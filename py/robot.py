#!/usr/bin/env python3

import wpilib
from networktables import NetworkTable
import keys

class Shooter :
    def __init__(self, **ports) :
        self.angleMotor = wpilib.CANTalon(ports["angle"])
        self.leftWheel = wpilib.CANTalon(ports["left"])
        self.rightWheel = wpilib.CANTalon(ports["right"])
        self.sonar = wpilib.AnalogInput(ports["sonar"])
        self.kicker = wpilib.Servo(ports["kicker"])

class MyRobot(wpilib.IterativeRobot):
    
    def robotInit(self):
        """
        This function is called upon program startup and
        should be used for any initialization code.
        """
        self.joy = wpilib.Joystick(0)
        self.right_talons = [wpilib.CANTalon(i) for i in (1,2)]
        self.left_talons = [wpilib.CANTalon(i) for i in (3,4)]
        self.shooter = Shooter(angle=8, left=5, right=6, sonar=0, kicker=0)
        self.dash = NetworkTable.getTable("SmartDashboard")
        self.dash.putBoolean(keys.KEY_VISION, False)
        self.dash.putBoolean(keys.KEY_FOUND, False)
        self.dash.putNumber(keys.KEY_X, 0.0)
        self.dash.putNumber(keys.KEY_Y, 0.0)
        self.dash.putNumber(keys.KEY_ANG, 0.0)

    def autonomousInit(self) :
        self.dash.putBoolean(keys.KEY_VISION, True)

    def autonomousPeriodic(self):
        """This function is called periodically during autonomous."""
        try :
            found = self.dash.getBoolean(keys.KEY_FOUND)
        except :
            pass

    def teleopInit(self) :
        self.dash.putBoolean(keys.KEY_VISION, False)

    def teleopPeriodic(self):
        """This function is called periodically during operator control."""
        self.dash.putBoolean(keys.KEY_VISION, self.joy.getRawButton(3)) 

    def disabledPeriodic(self):
        """This function is called periodically during test mode."""
        pass

    def testPeriodic(self):
        """This function is called periodically during test mode."""
        pass

if __name__ == "__main__":
    wpilib.run(MyRobot)
