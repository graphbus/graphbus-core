"""
Kubernetes command - Generate K8s manifests and manage deployments
"""

import click
import subprocess
from pathlib import Path
from typing import Optional

from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header, print_warning
)
from graphbus_cli.utils.errors import CLIError


@click.group()
def k8s():
    """
    Kubernetes deployment tools.

    \b
    Generate Kubernetes manifests and deploy GraphBus applications.

    \b
    Examples:
      graphbus k8s generate                 # Generate K8s manifests
      graphbus k8s generate --with-autoscaler  # Include HPA
      graphbus k8s apply                    # Apply manifests to cluster
      graphbus k8s status                   # Check deployment status
    """
    pass


@k8s.command()
@click.option(
    '--output-dir',
    '-o',
    type=click.Path(file_okay=False),
    default='k8s',
    help='Output directory for manifests (default: k8s/)'
)
@click.option(
    '--namespace',
    default='default',
    help='Kubernetes namespace (default: default)'
)
@click.option(
    '--replicas',
    type=int,
    default=3,
    help='Number of replicas (default: 3)'
)
@click.option(
    '--image',
    default='graphbus-app:latest',
    help='Docker image (default: graphbus-app:latest)'
)
@click.option(
    '--with-autoscaler',
    is_flag=True,
    help='Include HorizontalPodAutoscaler'
)
@click.option(
    '--with-ingress',
    is_flag=True,
    help='Include Ingress resource'
)
@click.option(
    '--with-configmap',
    is_flag=True,
    help='Include ConfigMap for configuration'
)
@click.option(
    '--with-pvc',
    is_flag=True,
    help='Include PersistentVolumeClaim for state'
)
def generate(
    output_dir: str,
    namespace: str,
    replicas: int,
    image: str,
    with_autoscaler: bool,
    with_ingress: bool,
    with_configmap: bool,
    with_pvc: bool
):
    """
    Generate Kubernetes manifests for GraphBus application.

    \b
    Creates a complete set of K8s manifests:
      - Deployment with replica sets
      - Service for internal/external access
      - ConfigMap for configuration (optional)
      - PersistentVolumeClaim for state (optional)
      - HorizontalPodAutoscaler (optional)
      - Ingress (optional)
    """
    try:
        print_header("Generating Kubernetes Manifests")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate deployment
        deployment = _generate_deployment(
            namespace=namespace,
            replicas=replicas,
            image=image,
            with_configmap=with_configmap,
            with_pvc=with_pvc
        )
        (output_path / "deployment.yaml").write_text(deployment)
        print_success("Generated deployment.yaml")

        # Generate service
        service = _generate_service(namespace=namespace)
        (output_path / "service.yaml").write_text(service)
        print_success("Generated service.yaml")

        # Generate ConfigMap if requested
        if with_configmap:
            configmap = _generate_configmap(namespace=namespace)
            (output_path / "configmap.yaml").write_text(configmap)
            print_success("Generated configmap.yaml")

        # Generate PVC if requested
        if with_pvc:
            pvc = _generate_pvc(namespace=namespace)
            (output_path / "pvc.yaml").write_text(pvc)
            print_success("Generated pvc.yaml")

        # Generate HPA if requested
        if with_autoscaler:
            hpa = _generate_hpa(namespace=namespace, replicas=replicas)
            (output_path / "hpa.yaml").write_text(hpa)
            print_success("Generated hpa.yaml")

        # Generate Ingress if requested
        if with_ingress:
            ingress = _generate_ingress(namespace=namespace)
            (output_path / "ingress.yaml").write_text(ingress)
            print_success("Generated ingress.yaml")

        console.print()
        print_success(f"All manifests generated in {output_dir}/")
        console.print()

        # Show next steps
        print_info("Next steps:")
        console.print(f"  1. Review manifests in {output_dir}/")
        console.print(f"  2. Apply: kubectl apply -f {output_dir}/")
        console.print("  3. Check status: kubectl get pods")
        console.print("  4. View logs: kubectl logs -l app=graphbus")

    except Exception as e:
        raise CLIError(f"Failed to generate Kubernetes manifests: {str(e)}")


@k8s.command()
@click.option(
    '--manifest-dir',
    '-f',
    type=click.Path(exists=True, file_okay=False),
    default='k8s',
    help='Manifest directory (default: k8s/)'
)
@click.option(
    '--namespace',
    default='default',
    help='Kubernetes namespace (default: default)'
)
def apply(manifest_dir: str, namespace: str):
    """
    Apply Kubernetes manifests to cluster.

    \b
    Deploys the GraphBus application to Kubernetes.
    """
    try:
        print_header(f"Applying Manifests to Namespace: {namespace}")

        manifest_path = Path(manifest_dir)
        if not manifest_path.exists():
            print_error(f"{manifest_dir} not found")
            print_info("Generate manifests with: graphbus k8s generate")
            raise click.Abort()

        # Apply manifests
        cmd = ['kubectl', 'apply', '-f', str(manifest_path), '-n', namespace]

        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
        console.print()

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print(result.stdout)
            print_success("Manifests applied successfully")
        else:
            print_error(result.stderr)
            raise CLIError(f"kubectl apply failed with exit code {result.returncode}")

    except FileNotFoundError:
        raise CLIError("kubectl not found. Please install kubectl first.")
    except Exception as e:
        raise CLIError(f"Failed to apply manifests: {str(e)}")


@k8s.command()
@click.option(
    '--namespace',
    default='default',
    help='Kubernetes namespace (default: default)'
)
def status(namespace: str):
    """
    Check status of GraphBus deployment.

    \b
    Shows status of pods, services, and deployments.
    """
    try:
        print_header(f"Deployment Status (Namespace: {namespace})")

        # Get pods
        cmd = ['kubectl', 'get', 'pods', '-l', 'app=graphbus', '-n', namespace]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[bold cyan]Pods:[/bold cyan]")
            console.print(result.stdout)
        else:
            print_warning("No pods found")

        console.print()

        # Get deployments
        cmd = ['kubectl', 'get', 'deployment', 'graphbus-runtime', '-n', namespace]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[bold cyan]Deployment:[/bold cyan]")
            console.print(result.stdout)

        console.print()

        # Get services
        cmd = ['kubectl', 'get', 'service', 'graphbus-service', '-n', namespace]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[bold cyan]Service:[/bold cyan]")
            console.print(result.stdout)

    except FileNotFoundError:
        raise CLIError("kubectl not found. Please install kubectl first.")
    except Exception as e:
        raise CLIError(f"Failed to get status: {str(e)}")


@k8s.command()
@click.option(
    '--namespace',
    default='default',
    help='Kubernetes namespace (default: default)'
)
@click.option(
    '--follow',
    '-f',
    is_flag=True,
    help='Follow log output'
)
def logs(namespace: str, follow: bool):
    """
    View logs from GraphBus pods.

    \b
    Streams logs from all GraphBus pods.
    """
    try:
        print_header(f"GraphBus Logs (Namespace: {namespace})")

        # Get logs
        cmd = ['kubectl', 'logs', '-l', 'app=graphbus', '-n', namespace]
        if follow:
            cmd.append('-f')

        result = subprocess.run(cmd, capture_output=False)

        if result.returncode != 0:
            raise CLIError(f"kubectl logs failed with exit code {result.returncode}")

    except FileNotFoundError:
        raise CLIError("kubectl not found. Please install kubectl first.")
    except KeyboardInterrupt:
        console.print()
        print_info("Stopped following logs")
    except Exception as e:
        raise CLIError(f"Failed to get logs: {str(e)}")


def _generate_deployment(
    namespace: str,
    replicas: int,
    image: str,
    with_configmap: bool,
    with_pvc: bool
) -> str:
    """Generate Deployment manifest"""

    manifest = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: graphbus-runtime
  namespace: {namespace}
  labels:
    app: graphbus
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: graphbus
  template:
    metadata:
      labels:
        app: graphbus
    spec:
      containers:
      - name: graphbus
        image: {image}
        ports:
        - containerPort: 8080
          name: http
"""

    # Add environment variables from ConfigMap
    if with_configmap:
        manifest += """        envFrom:
        - configMapRef:
            name: graphbus-config
"""

    # Add volume mounts for PVC
    if with_pvc:
        manifest += """        volumeMounts:
        - name: graphbus-state
          mountPath: /app/state
"""

    # Add resource limits
    manifest += """        resources:
          limits:
            cpu: "1"
            memory: "1Gi"
          requests:
            cpu: "100m"
            memory: "128Mi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
"""

    # Add volumes section if using PVC
    if with_pvc:
        manifest += """      volumes:
      - name: graphbus-state
        persistentVolumeClaim:
          claimName: graphbus-pvc
"""

    return manifest


def _generate_service(namespace: str) -> str:
    """Generate Service manifest"""

    return f"""apiVersion: v1
kind: Service
metadata:
  name: graphbus-service
  namespace: {namespace}
  labels:
    app: graphbus
spec:
  type: ClusterIP
  ports:
  - port: 8080
    targetPort: 8080
    protocol: TCP
    name: http
  selector:
    app: graphbus
"""


def _generate_configmap(namespace: str) -> str:
    """Generate ConfigMap manifest"""

    return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: graphbus-config
  namespace: {namespace}
data:
  GRAPHBUS_ENV: "production"
  GRAPHBUS_LOG_LEVEL: "info"
  GRAPHBUS_ENABLE_STATE_PERSISTENCE: "true"
  GRAPHBUS_ENABLE_HEALTH_MONITORING: "true"
"""


def _generate_pvc(namespace: str) -> str:
    """Generate PersistentVolumeClaim manifest"""

    return f"""apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: graphbus-pvc
  namespace: {namespace}
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
"""


def _generate_hpa(namespace: str, replicas: int) -> str:
    """Generate HorizontalPodAutoscaler manifest"""

    return f"""apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: graphbus-hpa
  namespace: {namespace}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: graphbus-runtime
  minReplicas: {replicas}
  maxReplicas: {replicas * 3}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
"""


def _generate_ingress(namespace: str) -> str:
    """Generate Ingress manifest"""

    return f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: graphbus-ingress
  namespace: {namespace}
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: graphbus.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: graphbus-service
            port:
              number: 8080
"""
