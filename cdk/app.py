#!/usr/bin/env python3
"""
cdk/app.py  —  CDK entry point
Run: cdk deploy
"""
import aws_cdk as cdk
from med_safety_stack import MedSafetyStack

app = cdk.App()
MedSafetyStack(app, "MedSafetyStack",
    env=cdk.Environment(region="us-east-1")   # Change region if needed
)
app.synth()
