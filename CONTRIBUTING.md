# Contributing to HeatSafeNet

Thank you for your interest in contributing to HeatSafeNet! This project aims to provide open-source tools for optimizing climate resilience infrastructure.

## Getting Started

### Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/heatsafenet.git
   cd heatsafenet
   ```

3. Create the development environment:
   ```bash
   make env
   conda activate heatsafenet
   ```

4. Install development dependencies:
   ```bash
   pip install -e .
   pre-commit install  # If using pre-commit hooks
   ```

### Development Workflow

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards
3. Test your changes:
   ```bash
   make test
   make lint
   ```

4. Commit your changes with descriptive messages
5. Push to your fork and create a pull request

## Code Standards

### Python Code Style

- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://isort.readthedocs.io/) for import sorting
- Follow PEP 8 naming conventions
- Add type hints where appropriate
- Document all functions and classes with docstrings

Example:
```python
def compute_risk_score(heat: float, social: float, digital: float) -> float:
    """
    Compute composite risk score from components.
    
    Args:
        heat: Heat exposure score (0-1)
        social: Social vulnerability score (0-1) 
        digital: Digital exclusion score (0-1)
        
    Returns:
        Composite risk score (0-1)
    """
    return 0.5 * heat + 0.3 * social + 0.2 * digital
```

### Testing

- Write unit tests for new functions
- Use meaningful test names
- Test edge cases and error conditions
- Place tests in the `tests/` directory

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all public functions
- Update API documentation for web service changes
- Include examples in docstrings when helpful

## Types of Contributions

### Bug Reports

When filing bug reports, please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Python version, etc.)
- Relevant error messages or logs

### Feature Requests

For feature requests, please describe:
- The problem you're trying to solve
- Proposed solution
- Alternative approaches considered
- Potential impact on existing functionality

### Code Contributions

We welcome contributions in these areas:

**Data Processing**
- Additional data sources (climate, demographic, infrastructure)
- Data quality validation
- Performance optimizations

**Risk Modeling**
- New risk components
- Alternative weighting schemes
- Validation methodologies

**Optimization**
- Alternative optimization algorithms
- Performance improvements
- Constraint handling

**Visualization**
- Interactive map features
- Static figure improvements
- Dashboard enhancements

**Infrastructure**
- CI/CD improvements
- Documentation generation
- Deployment automation

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows style guidelines (run `make format`)
- [ ] All tests pass (run `make test`)
- [ ] No linting errors (run `make lint`)
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] All existing tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

## Data Contributions

### New Data Sources

When adding new data sources:

1. Ensure data is publicly available
2. Document data licensing and attribution
3. Add data fetching scripts to `src/etl/`
4. Include data validation checks
5. Update documentation with data descriptions

### Geographic Extensions

To add new geographic areas:

1. Update county configurations in ETL scripts
2. Ensure data sources cover new areas
3. Test full pipeline with new geography
4. Update documentation and examples

## Research Contributions

### Academic Collaboration

We welcome collaborations with researchers:
- Validation studies using different datasets
- Methodological improvements
- Comparative analysis with other approaches
- Policy impact assessments

### Publications

If using HeatSafeNet in research:
- Please cite our work appropriately
- Consider co-authoring opportunities
- Share results that could benefit the community

## Community Guidelines

### Code of Conduct

This project adheres to a code of professional conduct:
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and contribute
- Maintain professional communication

### Getting Help

- Check existing documentation and issues first
- Use GitHub issues for bug reports and feature requests
- Join discussions in GitHub Discussions
- Contact maintainers for urgent matters

## Recognition

Contributors will be acknowledged in:
- Repository contributors list
- Project documentation
- Research publications (when appropriate)
- Release notes for significant contributions

## Development Resources

### Useful Tools

- **Code Quality**: black, isort, ruff, mypy
- **Testing**: pytest, coverage
- **Geographic**: geopandas, shapely, contextily
- **Optimization**: ortools, pulp
- **Visualization**: matplotlib, seaborn, folium
- **Web**: FastAPI, Leaflet

### Learning Resources

- [GeoPandas documentation](https://geopandas.org/)
- [OR-Tools optimization guide](https://developers.google.com/optimization)
- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/)
- [Leaflet mapping guide](https://leafletjs.com/examples.html)

## License

By contributing to HeatSafeNet, you agree that your contributions will be licensed under the project's MIT License.

## Questions?

Feel free to reach out:
- Open an issue for technical questions
- Use GitHub Discussions for general questions
- Email maintainers for sensitive matters

Thank you for contributing to climate resilience research and tools!