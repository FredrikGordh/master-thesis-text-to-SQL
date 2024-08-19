# Master's Thesis: Evaluation of Text-To-SQL Agents on BIRD-Bench

## Overview

This repository contains the code and experiments related to our, Fredrik Gordh & [Niklas Wretblad's](https://github.com/niklaswretblad), master's thesis, where we explore and evaluate different Text-To-SQL agents, including DIN-SQL, few-shot, and zero-shot models. The evaluation is conducted using the BIRD-Bench dataset, with a particular focus on the financial domain.

The master's thesis lead to a research paper published and presented in ACL.

- **Research Paper:** [ACL 2024 Short Paper](https://aclanthology.org/2024.acl-short.34/)
- **Master's Thesis:** [Linköping University Thesis](https://liu.diva-portal.org/smash/get/diva2:1833681/FULLTEXT02.pdf)

## Table of Contents
- [Introduction](#introduction)
- [Dataset](#dataset)
- [Models](#models)
  - [DIN-SQL](#din-sql)
  - [Few-Shot Learning](#few-shot-learning)
  - [Zero-Shot Learning](#zero-shot-learning)
- [Evaluation](#evaluation)
  - [BIRD-Bench](#bird-bench)
  - [Financial Domain](#financial-domain)
- [Results](#results)
- [Installation](#installation)
- [Usage](#usage)
- [Contributors](#contributors)
- [License](#license)

## Introduction

In this project, we investigate the performance of various Text-To-SQL agents on the BIRD-Bench dataset. Our focus is on understanding how these models generalize to different domains, particularly the financial domain. Text-To-SQL agents are crucial for enabling non-expert users to interact with databases using natural language queries.

## Dataset

### BIRD-Bench

[BIRD-Bench](https://bird-bench.github.io/) is a comprehensive benchmark dataset for evaluating Text-To-SQL systems across various domains. The dataset includes several subdomains, with the financial domain being a key area of interest for our research.

## Models

### DIN-SQL

[DIN-SQL](https://github.com/MohammadrezaPourreza/Few-shot-NL2SQL-with-prompting) is a state-of-the-art Text-To-SQL agent known for its ability to generate accurate SQL queries from natural language inputs. We have implemented and evaluated DIN-SQL on the BIRD-Bench dataset.

### Few-Shot Learning

Few-shot learning models are designed to perform well even with a limited number of training examples. We experimented with few-shot techniques to understand their applicability to Text-To-SQL tasks.

### Zero-Shot Learning

Zero-shot learning models are evaluated to determine their effectiveness in generating SQL queries without any task-specific training data. This is particularly relevant for domains where labeled data is scarce.

## Evaluation

### BIRD-Bench

We evaluated all the models on the entire BIRD-Bench dataset, analyzing their performance across different domains.

### Financial Domain

Given the importance of the financial sector, we conducted a detailed evaluation of the models on the financial domain subset of BIRD-Bench.

## Results
To view our results of the experiments, please see our master's thesis paper or the published research paper.
The results of our evaluations
