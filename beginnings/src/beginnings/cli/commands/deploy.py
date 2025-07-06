"""Deployment validation and utilities commands."""

import click
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ..utils.colors import success, error, info, warning, highlight
from ..utils.errors import ProjectError


@click.group(name="deploy")
def deploy_group():
    """Deployment validation and utilities commands."""
    pass


@click.command(name="validate")
@click.option(
    "--environment", "-e",
    type=click.Choice(["development", "staging", "production"]),
    default="production",
    help="Target deployment environment"
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Configuration file to validate"
)
@click.option(
    "--docker", 
    is_flag=True,
    help="Validate Docker configuration"
)
@click.option(
    "--kubernetes", "-k",
    is_flag=True,
    help="Validate Kubernetes configuration"
)
@click.option(
    "--cloud-provider",
    type=click.Choice(["aws", "gcp", "azure"]),
    help="Validate cloud provider configuration"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output validation report to file"
)
@click.pass_context
def validate_deployment(
    ctx: click.Context,
    environment: str,
    config: Optional[str],
    docker: bool,
    kubernetes: bool,
    cloud_provider: Optional[str],
    output: Optional[str]
):
    """Validate application deployment readiness."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    if not quiet:
        click.echo(info(f"Validating deployment for {environment} environment"))
        click.echo()
    
    try:
        from ...production import (
            ProductionValidator,
            EnvironmentManager,
            ProductionConfiguration
        )
        from ...deployment import DeploymentValidator, DeploymentConfiguration
        
        validation_results = {
            "environment": environment,
            "timestamp": click.datetime.now().isoformat(),
            "validation_results": {},
            "overall_status": "passed",
            "issues": [],
            "recommendations": []
        }
        
        # Load configuration
        if config:
            config_path = Path(config)
        else:
            config_path = _find_config_file()
        
        if not config_path or not config_path.exists():
            raise ProjectError("No configuration file found")
        
        app_config = _load_config_file(config_path)
        
        # Initialize validators
        env_manager = EnvironmentManager()
        prod_validator = ProductionValidator()
        deploy_validator = DeploymentValidator()
        
        # Create production configuration
        prod_config = ProductionConfiguration(
            environment=environment,
            security_level="strict" if environment == "production" else "standard",
            compliance_requirements=["SOC2"] if environment == "production" else [],
            monitoring_enabled=True,
            logging_level="WARNING" if environment == "production" else "INFO"
        )
        
        # 1. Environment Configuration Validation
        if verbose:
            click.echo(info("Validating environment configuration..."))
        
        env_result = env_manager.validate_environment(app_config, environment)
        validation_results["validation_results"]["environment"] = {
            "passed": env_result.is_valid,
            "issues": env_result.issues,
            "score": env_result.security_score
        }
        
        if not env_result.is_valid:
            validation_results["overall_status"] = "failed"
            validation_results["issues"].extend([f"Environment: {issue}" for issue in env_result.issues])
        
        # 2. Security Configuration Validation
        if verbose:
            click.echo(info("Validating security configuration..."))
        
        security_result = prod_validator.validate_security_configuration(app_config, prod_config)
        validation_results["validation_results"]["security"] = {
            "passed": security_result.passed,
            "issues": security_result.issues,
            "compliance_score": security_result.compliance_score
        }
        
        if not security_result.passed:
            validation_results["overall_status"] = "failed"
            validation_results["issues"].extend([f"Security: {issue}" for issue in security_result.issues])
        
        # 3. Network Configuration Validation
        if verbose:
            click.echo(info("Validating network configuration..."))
        
        network_result = prod_validator.validate_network_configuration(app_config)
        validation_results["validation_results"]["network"] = {
            "passed": network_result.passed,
            "issues": network_result.issues
        }
        
        if not network_result.passed:
            validation_results["overall_status"] = "failed"
            validation_results["issues"].extend([f"Network: {issue}" for issue in network_result.issues])
        
        # 4. Docker Configuration Validation
        if docker or _has_docker_config():
            if verbose:
                click.echo(info("Validating Docker configuration..."))
            
            docker_result = deploy_validator.validate_docker_configuration(app_config)
            validation_results["validation_results"]["docker"] = {
                "passed": docker_result.passed,
                "issues": docker_result.issues
            }
            
            if not docker_result.passed:
                validation_results["overall_status"] = "failed"
                validation_results["issues"].extend([f"Docker: {issue}" for issue in docker_result.issues])
        
        # 5. Kubernetes Configuration Validation
        if kubernetes or _has_kubernetes_config():
            if verbose:
                click.echo(info("Validating Kubernetes configuration..."))
            
            k8s_result = deploy_validator.validate_kubernetes_configuration(app_config)
            validation_results["validation_results"]["kubernetes"] = {
                "passed": k8s_result.passed,
                "issues": k8s_result.issues
            }
            
            if not k8s_result.passed:
                validation_results["overall_status"] = "failed"
                validation_results["issues"].extend([f"Kubernetes: {issue}" for issue in k8s_result.issues])
        
        # 6. Cloud Provider Validation
        if cloud_provider:
            if verbose:
                click.echo(info(f"Validating {cloud_provider.upper()} configuration..."))
            
            cloud_result = deploy_validator.validate_cloud_configuration(app_config, cloud_provider)
            validation_results["validation_results"][f"cloud_{cloud_provider}"] = {
                "passed": cloud_result.passed,
                "issues": cloud_result.issues
            }
            
            if not cloud_result.passed:
                validation_results["overall_status"] = "failed"
                validation_results["issues"].extend([f"{cloud_provider.upper()}: {issue}" for issue in cloud_result.issues])
        
        # 7. Compliance Validation for Production
        if environment == "production":
            if verbose:
                click.echo(info("Validating compliance requirements..."))
            
            compliance_result = prod_validator.validate_compliance(app_config, ["SOC2", "GDPR"])
            validation_results["validation_results"]["compliance"] = {
                "passed": compliance_result.passed,
                "issues": compliance_result.issues,
                "compliance_score": compliance_result.compliance_score
            }
            
            if not compliance_result.passed:
                validation_results["overall_status"] = "failed"
                validation_results["issues"].extend([f"Compliance: {issue}" for issue in compliance_result.issues])
        
        # Generate recommendations
        validation_results["recommendations"] = _generate_deployment_recommendations(
            validation_results, environment
        )
        
        # Display results
        if not quiet:
            _display_validation_results(validation_results, verbose)
        
        # Export results if requested
        if output:
            _export_validation_results(validation_results, output)
            if not quiet:
                click.echo(success(f"Validation report exported to: {output}"))
        
        # Exit with appropriate code
        if validation_results["overall_status"] == "failed":
            if not quiet:
                click.echo(error("Deployment validation failed"))
            ctx.exit(1)
        else:
            if not quiet:
                click.echo(success("Deployment validation passed"))
    
    except ImportError as e:
        raise ProjectError(f"Production utilities not available: {e}")
    except Exception as e:
        raise ProjectError(f"Deployment validation failed: {e}")


@click.command(name="check")
@click.option(
    "--environment", "-e",
    type=click.Choice(["development", "staging", "production"]),
    default="production",
    help="Target deployment environment"
)
@click.option(
    "--health-checks",
    is_flag=True,
    help="Run health checks on deployed application"
)
@click.option(
    "--url",
    type=str,
    help="Application URL to check"
)
@click.pass_context
def check_deployment(
    ctx: click.Context,
    environment: str,
    health_checks: bool,
    url: Optional[str]
):
    """Check deployed application health and status."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    if not quiet:
        click.echo(info(f"Checking deployment status for {environment} environment"))
    
    try:
        from ...monitoring import HealthManager
        from ...deployment import DeploymentMonitor
        
        # Initialize monitoring
        health_manager = HealthManager()
        deploy_monitor = DeploymentMonitor()
        
        # Check application health
        if url:
            if verbose:
                click.echo(info(f"Checking application health at: {url}"))
            
            health_result = deploy_monitor.check_application_health(url)
            
            if health_result.healthy:
                click.echo(success("Application is healthy"))
                if verbose:
                    click.echo(f"  Response time: {health_result.response_time_ms}ms")
                    click.echo(f"  Status code: {health_result.status_code}")
            else:
                click.echo(error("Application health check failed"))
                click.echo(f"  Error: {health_result.error}")
                ctx.exit(1)
        
        # Run comprehensive health checks
        if health_checks:
            if verbose:
                click.echo(info("Running comprehensive health checks..."))
            
            health_results = health_manager.run_all_health_checks()
            
            healthy_checks = sum(1 for result in health_results.values() if result.healthy)
            total_checks = len(health_results)
            
            if healthy_checks == total_checks:
                click.echo(success(f"All health checks passed ({healthy_checks}/{total_checks})"))
            else:
                click.echo(warning(f"Health checks: {healthy_checks}/{total_checks} passed"))
                
                for check_name, result in health_results.items():
                    if not result.healthy:
                        click.echo(f"  ✗ {check_name}: {result.error}")
    
    except ImportError:
        raise ProjectError("Monitoring utilities not available")
    except Exception as e:
        raise ProjectError(f"Deployment check failed: {e}")


def _find_config_file() -> Optional[Path]:
    """Find configuration file in project."""
    candidates = [
        "config/app.yaml",
        "config/app.yml", 
        "config.yaml",
        "config.yml",
        "app.yaml",
        "app.yml"
    ]
    
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    
    return None


def _load_config_file(config_path: Path) -> Dict[str, Any]:
    """Load configuration file."""
    with open(config_path, 'r') as f:
        if config_path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif config_path.suffix == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {config_path.suffix}")


def _has_docker_config() -> bool:
    """Check if Docker configuration exists."""
    docker_files = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]
    return any(Path(f).exists() for f in docker_files)


def _has_kubernetes_config() -> bool:
    """Check if Kubernetes configuration exists."""
    k8s_patterns = ["k8s/", "kubernetes/", "*.k8s.yaml", "*.k8s.yml"]
    
    # Check for directories
    for pattern in ["k8s", "kubernetes"]:
        if Path(pattern).is_dir():
            return True
    
    # Check for files
    for pattern in ["*.k8s.yaml", "*.k8s.yml"]:
        if list(Path(".").glob(pattern)):
            return True
    
    return False


def _generate_deployment_recommendations(
    validation_results: Dict[str, Any], 
    environment: str
) -> List[str]:
    """Generate deployment recommendations based on validation results."""
    recommendations = []
    
    results = validation_results["validation_results"]
    
    # Security recommendations
    if "security" in results and not results["security"]["passed"]:
        recommendations.append("Review and fix security configuration issues")
        recommendations.append("Consider running: beginnings config audit --compliance SOC2")
    
    # Environment recommendations
    if "environment" in results and not results["environment"]["passed"]:
        recommendations.append("Update environment configuration for production readiness")
        recommendations.append("Consider running: beginnings config fix --type environment")
    
    # Docker recommendations
    if "docker" in results and not results["docker"]["passed"]:
        recommendations.append("Fix Docker configuration issues")
        recommendations.append("Ensure Dockerfile follows security best practices")
    
    # Kubernetes recommendations  
    if "kubernetes" in results and not results["kubernetes"]["passed"]:
        recommendations.append("Update Kubernetes manifests for production deployment")
        recommendations.append("Review resource limits and security contexts")
    
    # Compliance recommendations
    if environment == "production" and "compliance" in results and not results["compliance"]["passed"]:
        recommendations.append("Address compliance violations before production deployment")
        recommendations.append("Consider consulting security team for compliance requirements")
    
    return recommendations


def _display_validation_results(validation_results: Dict[str, Any], verbose: bool) -> None:
    """Display validation results."""
    click.echo(highlight("Deployment Validation Results"))
    click.echo("=" * 50)
    
    overall_status = validation_results["overall_status"]
    status_color = success if overall_status == "passed" else error
    click.echo(f"Overall Status: {status_color(overall_status.upper())}")
    
    results = validation_results["validation_results"]
    
    # Display individual validation results
    for category, result in results.items():
        status = "✓" if result["passed"] else "✗"
        status_color = success if result["passed"] else error
        click.echo(f"{status} {category.title()}: {status_color('PASSED' if result['passed'] else 'FAILED')}")
        
        if verbose and result["issues"]:
            for issue in result["issues"]:
                click.echo(f"    • {issue}")
    
    # Display issues
    if validation_results["issues"]:
        click.echo(f"\n{error('Issues Found:')}")
        for issue in validation_results["issues"]:
            click.echo(f"  • {issue}")
    
    # Display recommendations
    if validation_results["recommendations"]:
        click.echo(f"\n{info('Recommendations:')}")
        for rec in validation_results["recommendations"]:
            click.echo(f"  • {rec}")


def _export_validation_results(validation_results: Dict[str, Any], output_path: str) -> None:
    """Export validation results to file."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    if output.suffix == '.json':
        with open(output, 'w') as f:
            json.dump(validation_results, f, indent=2)
    elif output.suffix in ['.yaml', '.yml']:
        with open(output, 'w') as f:
            yaml.dump(validation_results, f, default_flow_style=False)
    else:
        # Default to JSON
        with open(output.with_suffix('.json'), 'w') as f:
            json.dump(validation_results, f, indent=2)


# Add commands to the group
deploy_group.add_command(validate_deployment)
deploy_group.add_command(check_deployment)