"""
CI/CD command - Generate CI/CD pipeline templates
"""

import click
from pathlib import Path

from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header, print_warning
)
from graphbus_cli.utils.errors import CLIError


@click.command()
@click.option(
    '--provider',
    type=click.Choice(['github', 'gitlab', 'jenkins'], case_sensitive=False),
    default='github',
    help='CI/CD provider (default: github)'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(dir_okay=False),
    help='Output file path (auto-detected by default)'
)
@click.option(
    '--with-docker',
    is_flag=True,
    help='Include Docker build and push steps'
)
@click.option(
    '--with-k8s',
    is_flag=True,
    help='Include Kubernetes deployment steps'
)
def ci(provider: str, output: str, with_docker: bool, with_k8s: bool):
    """
    Generate CI/CD pipeline templates.

    \b
    Creates CI/CD configuration files for:
      - GitHub Actions
      - GitLab CI
      - Jenkins

    \b
    Pipeline includes:
      - Dependency installation
      - Agent validation
      - Unit tests
      - Build artifacts
      - Optional Docker build
      - Optional K8s deployment

    \b
    Examples:
      graphbus ci --provider github          # Generate GitHub Actions
      graphbus ci --provider gitlab          # Generate GitLab CI
      graphbus ci --provider github --with-docker  # Include Docker
    """
    try:
        print_header(f"Generating {provider.upper()} CI/CD Pipeline")

        # Determine output path
        if output:
            output_path = Path(output)
        else:
            output_path = _get_default_output_path(provider)

        # Check if file exists
        if output_path.exists():
            print_warning(f"{output_path} already exists")
            if not click.confirm("Overwrite?"):
                print_info("Cancelled")
                return

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate CI/CD config
        if provider == 'github':
            config = _generate_github_actions(with_docker, with_k8s)
        elif provider == 'gitlab':
            config = _generate_gitlab_ci(with_docker, with_k8s)
        elif provider == 'jenkins':
            config = _generate_jenkinsfile(with_docker, with_k8s)
        else:
            raise CLIError(f"Unsupported provider: {provider}")

        # Write to file
        output_path.write_text(config)

        print_success(f"Generated {output_path}")
        console.print()

        # Show next steps
        print_info("Next steps:")
        if provider == 'github':
            console.print("  1. Review .github/workflows/graphbus-ci.yml")
            console.print("  2. Commit and push to trigger workflow")
            console.print("  3. View results: github.com/<user>/<repo>/actions")
        elif provider == 'gitlab':
            console.print("  1. Review .gitlab-ci.yml")
            console.print("  2. Commit and push to trigger pipeline")
            console.print("  3. View results in GitLab CI/CD section")
        elif provider == 'jenkins':
            console.print("  1. Review Jenkinsfile")
            console.print("  2. Create Jenkins pipeline job")
            console.print("  3. Configure webhook for automatic triggers")

    except Exception as e:
        raise CLIError(f"Failed to generate CI/CD config: {str(e)}")


def _get_default_output_path(provider: str) -> Path:
    """Get default output path for provider"""
    if provider == 'github':
        return Path('.github/workflows/graphbus-ci.yml')
    elif provider == 'gitlab':
        return Path('.gitlab-ci.yml')
    elif provider == 'jenkins':
        return Path('Jenkinsfile')
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _generate_github_actions(with_docker: bool, with_k8s: bool) -> str:
    """Generate GitHub Actions workflow"""

    workflow = """name: GraphBus CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Validate agents
      run: |
        graphbus validate agents/ --strict

    - name: Run tests
      run: |
        pytest tests/ --cov=agents --cov-report=xml --cov-report=term

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

    - name: Build artifacts
      run: |
        graphbus build agents/

    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: graphbus-artifacts
        path: .graphbus/
"""

    if with_docker:
        workflow += """
  docker:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          ${{ secrets.DOCKER_USERNAME }}/graphbus-app:latest
          ${{ secrets.DOCKER_USERNAME }}/graphbus-app:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
"""

    if with_k8s:
        workflow += """
  deploy:
    needs: docker
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Set up kubectl
      uses: azure/setup-kubectl@v3

    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig

    - name: Deploy to Kubernetes
      run: |
        kubectl apply -f k8s/
        kubectl rollout status deployment/graphbus-runtime

    - name: Verify deployment
      run: |
        kubectl get pods -l app=graphbus
"""

    return workflow


def _generate_gitlab_ci(with_docker: bool, with_k8s: bool) -> str:
    """Generate GitLab CI pipeline"""

    pipeline = """image: python:3.11-slim

stages:
  - test
  - build
"""

    if with_docker:
        pipeline += "  - docker\n"

    if with_k8s:
        pipeline += "  - deploy\n"

    pipeline += """
variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

before_script:
  - pip install --upgrade pip
  - pip install -r requirements.txt

test:
  stage: test
  script:
    - pip install pytest pytest-cov
    - graphbus validate agents/ --strict
    - pytest tests/ --cov=agents --cov-report=xml --cov-report=term
    - graphbus build agents/
  coverage: '/^TOTAL.+?(\\d+\\%)$/'
  artifacts:
    paths:
      - .graphbus/
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
"""

    if with_docker:
        pipeline += """
docker:
  stage: docker
  image: docker:latest
  services:
    - docker:dind
  only:
    - main
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $CI_REGISTRY_IMAGE:latest -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:latest
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
"""

    if with_k8s:
        pipeline += """
deploy:
  stage: deploy
  image: bitnami/kubectl:latest
  only:
    - main
  script:
    - echo "$KUBE_CONFIG" | base64 -d > kubeconfig
    - export KUBECONFIG=kubeconfig
    - kubectl apply -f k8s/
    - kubectl rollout status deployment/graphbus-runtime
    - kubectl get pods -l app=graphbus
"""

    return pipeline


def _generate_jenkinsfile(with_docker: bool, with_k8s: bool) -> str:
    """Generate Jenkinsfile"""

    jenkinsfile = """pipeline {
    agent any

    environment {
        PYTHON_VERSION = '3.11'
    }

    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install pytest pytest-cov
                '''
            }
        }

        stage('Validate') {
            steps {
                sh '''
                    . venv/bin/activate
                    graphbus validate agents/ --strict
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests/ --cov=agents --cov-report=xml --cov-report=html
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                    publishHTML([
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
            }
        }

        stage('Build') {
            steps {
                sh '''
                    . venv/bin/activate
                    graphbus build agents/
                '''
            }
            post {
                success {
                    archiveArtifacts artifacts: '.graphbus/**/*', fingerprint: true
                }
            }
        }
"""

    if with_docker:
        jenkinsfile += """
        stage('Docker Build') {
            when {
                branch 'main'
            }
            steps {
                script {
                    docker.withRegistry('https://registry.hub.docker.com', 'docker-credentials') {
                        def image = docker.build("graphbus-app:${env.BUILD_ID}")
                        image.push('latest')
                        image.push("${env.BUILD_ID}")
                    }
                }
            }
        }
"""

    if with_k8s:
        jenkinsfile += """
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                withKubeConfig([credentialsId: 'k8s-credentials']) {
                    sh '''
                        kubectl apply -f k8s/
                        kubectl rollout status deployment/graphbus-runtime
                        kubectl get pods -l app=graphbus
                    '''
                }
            }
        }
"""

    jenkinsfile += """    }

    post {
        always {
            cleanWs()
        }
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}
"""

    return jenkinsfile
