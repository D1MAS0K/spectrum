# CLAUDE.md

## Project Overview

**Spectrum** — This is a newly initialized repository. Update this section as the project takes shape.

## Repository Structure

```
spectrum/
├── CLAUDE.md          # AI assistant guide (this file)
└── (empty)            # Project files to be added
```

> **Note:** This repository is freshly created with no existing code. Update this file as the project evolves.

## Getting Started

1. Clone the repository
2. Check out your feature branch
3. Add project files and update this document accordingly

## Development Workflow

### Branching

- Feature branches follow the pattern: `claude/<description>-<id>`
- Always develop on your assigned branch
- Never push directly to `main` without review

### Commits

- Use clear, descriptive commit messages
- Keep commits focused on a single logical change

### Git Operations

- Push with: `git push -u origin <branch-name>`
- Retry failed network operations up to 4 times with exponential backoff (2s, 4s, 8s, 16s)
- Fetch specific branches: `git fetch origin <branch-name>`

## Conventions

- Keep this file updated as the project grows
- Document new tooling, scripts, and architecture decisions here
- Follow existing code style and patterns once established

## AI Assistant Notes

- Read this file at the start of every session
- Always verify the current branch before making changes
- Run tests (once configured) before pushing
- Update this CLAUDE.md when adding significant new patterns or tooling
