"""
Pulumi deployment script for OpenClaw infrastructure
Supports Docker and cloud deployments
"""

import pulumi
import pulumi_docker as docker
import pulumi_aws as aws
from typing import Dict, Any
import json


def deploy_docker_local(config: Dict[str, Any]):
    """
    Deploy OpenClaw using Docker locally
    """
    # Create OpenClaw configuration file as a volume
    openclaw_config = config.get('openclaw_config', {})
    
    # Build or pull OpenClaw image
    openclaw_image = docker.RemoteImage(
        "openclaw-image",
        name="openclaw/openclaw:latest",
    )
    
    # Create Docker container
    openclaw_container = docker.Container(
        "openclaw-container",
        image=openclaw_image.repo_digest,
        name="openclaw",
        ports=[
            docker.ContainerPortArgs(
                internal=18789,
                external=18789,
            )
        ],
        restart="unless-stopped",
        envs=[
            f"ANTHROPIC_API_KEY={openclaw_config.get('env', {}).get('ANTHROPIC_API_KEY', '')}",
            f"OPENAI_API_KEY={openclaw_config.get('env', {}).get('OPENAI_API_KEY', '')}",
            "NODE_ENV=production",
        ],
    )
    
    pulumi.export("container_id", openclaw_container.id)
    pulumi.export("container_name", openclaw_container.name)
    
    return {
        "container_id": openclaw_container.id,
        "status": "deployed"
    }


def deploy_aws_ecs(config: Dict[str, Any]):
    """
    Deploy OpenClaw to AWS ECS (Fargate)
    """
    # Create VPC
    vpc = aws.ec2.Vpc(
        "openclaw-vpc",
        cidr_block="10.0.0.0/16",
        enable_dns_hostnames=True,
        enable_dns_support=True,
    )
    
    # Create subnet
    subnet = aws.ec2.Subnet(
        "openclaw-subnet",
        vpc_id=vpc.id,
        cidr_block="10.0.1.0/24",
        availability_zone="us-east-1a",
    )
    
    # Create ECS cluster
    cluster = aws.ecs.Cluster("openclaw-cluster")
    
    # Create task definition
    openclaw_config = config.get('openclaw_config', {})
    
    task_definition = aws.ecs.TaskDefinition(
        "openclaw-task",
        family="openclaw",
        cpu="256",
        memory="512",
        network_mode="awsvpc",
        requires_compatibilities=["FARGATE"],
        container_definitions=json.dumps([{
            "name": "openclaw",
            "image": "openclaw/openclaw:latest",
            "essential": True,
            "portMappings": [{
                "containerPort": 18789,
                "protocol": "tcp"
            }],
            "environment": [
                {
                    "name": "ANTHROPIC_API_KEY",
                    "value": openclaw_config.get('env', {}).get('ANTHROPIC_API_KEY', '')
                },
                {
                    "name": "OPENAI_API_KEY",
                    "value": openclaw_config.get('env', {}).get('OPENAI_API_KEY', '')
                },
                {
                    "name": "NODE_ENV",
                    "value": "production"
                }
            ]
        }])
    )
    
    # Create ECS service
    service = aws.ecs.Service(
        "openclaw-service",
        cluster=cluster.arn,
        desired_count=1,
        launch_type="FARGATE",
        task_definition=task_definition.arn,
        network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
            assign_public_ip=True,
            subnets=[subnet.id],
        ),
    )
    
    pulumi.export("cluster_name", cluster.name)
    pulumi.export("service_name", service.name)
    
    return {
        "cluster_arn": cluster.arn,
        "service_name": service.name,
        "status": "deployed"
    }


def main():
    """
    Main Pulumi program
    """
    # Get configuration from Pulumi config
    config = pulumi.Config()
    deployment_type = config.get("deployment_type") or "docker"
    
    # Get OpenClaw configuration
    openclaw_config_str = config.get("openclaw_config") or "{}"
    openclaw_config = json.loads(openclaw_config_str)
    
    deployment_config = {
        "openclaw_config": openclaw_config
    }
    
    if deployment_type == "docker":
        result = deploy_docker_local(deployment_config)
    elif deployment_type == "aws":
        result = deploy_aws_ecs(deployment_config)
    else:
        raise ValueError(f"Unknown deployment type: {deployment_type}")
    
    pulumi.export("deployment_status", result["status"])


if __name__ == "__main__":
    main()
