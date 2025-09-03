# Contributing to AirconnectAPI

Thank you for your interest in contributing to AirconnectAPI! We welcome contributions from everyone and are grateful for every contribution, no matter how small.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Issues

Before creating an issue, please:

1. **Search existing issues** to avoid duplicates
2. **Use a clear and descriptive title**
3. **Provide detailed information** about the bug or feature request
4. **Include steps to reproduce** for bugs
5. **Add relevant labels** to help categorize the issue

#### Bug Reports

When reporting bugs, please include:

- **Environment details** (OS, Python version, FastAPI version)
- **Steps to reproduce** the issue
- **Expected behavior** vs **actual behavior**
- **Error messages** or logs (if any)
- **Screenshots** (if applicable)

#### Feature Requests

When requesting features, please include:

- **Clear description** of the feature
- **Use case** or problem it solves
- **Proposed implementation** (if you have ideas)
- **Alternative solutions** you've considered

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/airconnectapi.git
   cd airconnectapi
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   # Or for development dependencies:
   pip install -e ".[dev]"
   ```

5. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Making Changes

#### Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **Ruff** for linting
- **MyPy** for static type checking
- **pytest** for testing

Before submitting your changes, please run:

```bash
# Format code
black .
isort .

# Lint and type check
ruff check .
mypy .

# Run tests
pytest
```

#### Commit Guidelines

- Use clear and meaningful commit messages
- Follow the format: `type(scope): description`
- Examples:
  - `feat(api): add user authentication endpoint`
  - `fix(auth): resolve token validation issue`
  - `docs(readme): update installation instructions`
  - `test(api): add tests for hello endpoint`

#### Code Guidelines

- **Write tests** for new features and bug fixes
- **Add docstrings** to functions and classes
- **Keep functions small** and focused
- **Use type hints** where appropriate
- **Follow PEP 8** style guidelines
- **Add comments** for complex logic

### Testing

- Write tests for all new functionality
- Ensure all tests pass before submitting
- Aim for good test coverage
- Use descriptive test names
- Group related tests in classes

Run tests with:
```bash
pytest
pytest --cov=openflight  # With coverage
```

### Documentation

- Update documentation for new features
- Add docstrings to new functions/classes
- Update README.md if needed
- Include examples in docstrings

### Submitting Changes

1. **Push your changes** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub with:
   - Clear title and description
   - Reference to related issues
   - Screenshots (if UI changes)
   - Checklist of completed items

3. **Respond to feedback** and make requested changes

4. **Ensure CI passes** before requesting review

### Pull Request Checklist

Before submitting a pull request, ensure:

- [ ] Code follows the project's style guidelines
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No merge conflicts
- [ ] CI/CD checks pass
- [ ] Related issues are referenced

## Development Workflow

### Branch Naming

Use descriptive branch names:
- `feature/add-user-auth`
- `fix/token-validation`
- `docs/api-documentation`
- `refactor/database-layer`

### Release Process

1. Features are merged into `main` branch
2. Releases are tagged with semantic versioning
3. Changelog is updated for each release

## Getting Help

If you need help:

- **Check the documentation** first
- **Search existing issues** and discussions
- **Ask questions** in GitHub Discussions
- **Join our community** (if applicable)

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

## License

By contributing to Airconnect API, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Airconnect API! 🚀