# GitHub Interaction Model — Agent Learning Spec

## Meta
{
  "document_id": "github_interaction_model",
  "version": "1.0.0",
  "purpose": "teach agent github collaboration logic"
}

---

## 1. Core Entities

- repository:
  container of code, includes files and version history

- branch:
  independent development line, used to isolate changes

- commit:
  atomic code change with diff, message, author

- pull_request:
  request to merge changes into main branch

- issue:
  discussion of problem or feature

- reviewer:
  actor responsible for validating changes

---

## 2. Core Actions

### 2.1 Upload Code

- modify files
- create commit
- push to repository

Result:
- new version created

---

### 2.2 Use Code

- clone repository
- import module
- fork and modify

Intent:
- reuse existing capability

---

### 2.3 Update Code (Pull Request)

- create branch
- implement changes
- push branch
- open pull request

Pull Request contains:
- code diff
- description
- discussion thread

Intent:
- propose change to shared system

---

### 2.4 Review Code

Actor:
- reviewer

Operations:
- comment on code
- request changes
- approve

Criteria:
- correctness
- readability
- performance
- consistency

Result:
- approved
- rejected
- needs modification

---

### 2.5 Merge Code

Condition:
- pull request approved
- checks passed

Result:
- main branch updated

---

## 3. Interaction Flow

Developer writes code  
→ push to branch  
→ open pull request  
→ review and discussion  
→ modify if needed  
→ approval  
→ merge into main  

---

## 4. Communication Model

- structured:
  - pull request comments
  - inline code comments

- semi-structured:
  - issues

- weak signals:
  - stars
  - forks

---

## 5. Principles

- changes are proposed, not directly applied
- discussion is attached to code context
- all changes are versioned
- validation is required before merge
- collaboration is asynchronous

---

## 6. Abstract Model

unit: change

flow:
- propose change
- discuss change
- validate change
- accept or reject

rule:
- no change enters main without validation

---

## 7. Agent Mapping

- commit → skill modification
- pull request → skill evolution request
- review → evaluation
- merge → new version release
- repository → skill registry

---

## 8. Agent Reasoning Template

input:
- need to improve system

process:
- identify target
- propose change
- generate diff
- submit for review
- wait for feedback
- iterate

output:
- updated system

---

## 9. Core Insight

- system is centered around change, not code
- interaction is structured, not conversational
- integration requires validation

---

## Final Statement

GitHub is a system where changes are proposed, reviewed, and merged in a structured workflow.