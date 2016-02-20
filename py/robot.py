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
        self.SRX = [wpilib.CANTalon(i) for i in range(4)]
        self.shooter = Shooter(angle=8, left=5, right=6, sonar=0, kicker=0)
        self.dash = NetworkTable.getTable("SmartDashboard")
        self.dash.putBoolean(keys.KEY_VISION, False)
        self.dash.putBoolean(keys.KEY_FOUND, False)
        self.dash.putNumber(keys.KEY_X, 0.0)
        self.dash.putNumber(keys.KEY_Y, 0.0)
        self.dash.putNumber(keys.KEY_ANG, 0.0)

    def autonomousInit(self) :
        print("autonomous init called")
        self.dash.putBoolean(keys.KEY_VISION, True)

    def autonomousPeriodic(self):
        """This function is called periodically during autonomous."""
        self.move_vel(*self.fwd_turn_from_vision())

    def fwd_turn_from_vision(self) :
        found = self.dash.getBoolean(keys.KEY_FOUND)
        if found :
            fwd = self.dash.getNumber(keys.KEY_Y)/100.
            turn = -self.dash.getNumber(keys.KEY_X)/320.
        else :
            fwd = 0.
            turn = 0.
        return fwd, turn

    def teleopInit(self) :
        print("teleop init called")
        self.dash.putBoolean(keys.KEY_VISION, False)

    def teleopPeriodic(self):
        """This function is called periodically during operator control."""
        if self.joy.getRawButton(3) :
            self.vision = True
            self.dash.putBoolean(keys.KEY_VISION, True)
        elif self.joy.getRawButton(4) :
            self.vision = False
            self.dash.putBoolean(keys.KEY_VISION, False)
        else :
            self.vision = self.dash.getBoolean(keys.KEY_VISION)
        if self.vision :
            fwd, turn = self.fwd_turn_from_vision()
        else :
            fwd, turn = -self.joy.getAxis(1), -self.joy.getAxis(0)
        self.move_vel(fwd, turn)

    def move_vel(self, fwd, turn) : 
        r,l = 0.5*fwd + 0.5*turn, 0.5*fwd - 0.5*turn
        r = max(min(0.25, r), -0.25)
        l = max(min(0.25, l), -0.25)
        self.SRX[0].set(r)
        self.SRX[3].set(l)

    def disabledInit(self) :
        print("disabled init called")
        self.dash.putBoolean(keys.KEY_VISION, False)

    def disabledPeriodic(self):
        """This function is called periodically while disabled."""
        pass

    def testInit(self) :
        print("test init called")
        self.dash.putBoolean(keys.KEY_VISION, False)

    def testPeriodic(self):
        """This function is called periodically during test mode."""
        pass

if __name__ == "__main__":
    wpilib.run(MyRobot)
