# Contributing to MERL-T

Thank you for your interest in contributing to MERL-T! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Types of Contributions](#types-of-contributions)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting Guidelines](#issue-reporting-guidelines)
- [Community and Communication](#community-and-communication)

## Code of Conduct

Our project is committed to fostering an open and welcoming environment. All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

## Project Structure

MERL-T is organized into several main components:

```
MERL-T/
├── src/
│   ├── data_lab/             # Data processing modules
│   │   ├── ner-giuridico/    # Legal Named Entity Recognition
│   │   ├── pdf_chunker/      # PDF processing tools
│   ├── orchestrator/         # MoE router and orchestration
│   ├── prompts/              # Template prompts for LLMs
│   ├── utils/
│   │   ├── visualex_api/     # API for legal document retrieval
├── tests/                    # Test suite
├── docs/                     # Documentation
├── .venv/                    # Virtual environment (not committed)
```

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- Docker (recommended for certain components)

### Initial Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/MERL-T.git
   cd MERL-T
   ```
3. Set up the upstream remote:
   ```bash
   git remote add upstream https://github.com/original-org/MERL-T.git
   ```
4. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
5. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
6. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Development Workflow

We follow a workflow based on feature branches and pull requests:

1. Create a branch for your feature or bug fix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-you-are-fixing
   ```

2. Make your changes, following the code standards outlined below

3. Run tests locally to ensure your changes don't break existing functionality:
   ```bash
   pytest
   ```

4. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "Add feature: detailed description of your changes"
   ```

5. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a pull request from your branch to the main repository

## Code Standards

### Python

- Follow PEP 8 style guide
- Use type hints where appropriate
- Write docstrings in Google style format
- Aim for 80% test coverage for new code
- Use meaningful variable and function names

Example:
```python
def process_legal_document(document_path: str, normalize: bool = True) -> Dict[str, Any]:
    """
    Process a legal document and extract structured information.
    
    Args:
        document_path: Path to the document file
        normalize: Whether to normalize extracted text
        
    Returns:
        Dictionary containing extracted information
        
    Raises:
        FileNotFoundError: If the document doesn't exist
    """
    # Implementation
```

### JavaScript/TypeScript

- Follow the ESLint configuration
- Use async/await instead of raw promises
- Document functions with JSDoc comments

## Types of Contributions

### Code Contributions

- **Core Components**: Work on the MoE architecture, router, or expert modules
- **API Development**: Enhance VisuaLex API or NER-Giuridico API
- **Performance Improvements**: Optimize existing components
- **Bug Fixes**: Address reported issues

### Documentation

- Improve installation instructions
- Add usage examples
- Create tutorials
- Add docstring to undocumented functions

### Knowledge Graph Contributions

- Add new entity relationships
- Validate existing relationships
- Enrich the ontology

### Dataset Contributions

- Annotate legal documents for NER training
- Validate the quality of existing annotations
- Contribute relevant legal documents for analysis

## Pull Request Process

1. **Title**: Use a clear, descriptive title that summarizes your changes
2. **Description**:
   - Describe the purpose of your changes
   - Reference any related issues with "Fixes #issue_number"
   - Explain your approach and design decisions
   - List any dependencies added
3. **Review Process**:
   - PRs require at least one review from a maintainer
   - Address all review comments
   - Ensure CI checks pass
4. **Merge**:
   - PR will be merged by a maintainer after approval
   - Typically, we use squash merging to keep the history clean

## Issue Reporting Guidelines

When reporting issues, please:

1. Check that the issue hasn't already been reported
2. Use a clear, descriptive title
3. Include steps to reproduce the issue
4. Describe expected vs. actual behavior
5. Include system information (OS, Python version, etc.)
6. Attach relevant logs if available

Use issue templates when available for:
- Bug reports
- Feature requests
- Documentation improvements

## Community and Communication

- **Discussion Forum**: [link to forum]
- **Slack/Discord**: [link to channel]
- **Project Meetings**: Every two weeks, see calendar for details
- **Mailing List**: [email address]

## Legal Considerations

As MERL-T deals with legal content, please be aware of the following:

- Do not include copyrighted legal materials without proper permission
- When contributing to the Knowledge Graph or datasets, ensure information accuracy
- Disclose any potential conflicts of interest

---

By contributing to MERL-T, you agree that your contributions will be licensed under the same license as the project (MIT for code, CC BY-SA for datasets and Knowledge Graph).

Thank you for helping to improve MERL-T! Together, we're making legal information more accessible and understandable through AI.
