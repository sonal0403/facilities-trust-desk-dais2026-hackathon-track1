# Databricks notebook source

# Quick test - can we run basic Python on serverless?
print("Hello from serverless!")
print(spark.table("databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities").count())
