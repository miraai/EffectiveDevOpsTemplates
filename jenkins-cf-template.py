"""Generating CloudFormation template."""
from ipaddress import ip_network
from ipify import get_ip
from troposphere import (
	Base64,
	ec2,
	GetAtt,
	Join,
	Output,
	Parameter,
	Ref,
	Template,
)

from troposphere.iam import (
	InstanceProfile,
	PolicyType as IAMPolicy,
	Role,
)

from awacs.aws import (
	Action,
	Allow,
	Policy,
	Principal,
	Statement,
)

from awacs.sts import AssumeRole

APP_NAME = 'jenkins'
APP_PORT = '8080'

GITHUB_USERNAME = 'miraai'
GITHUB_BASE_URL = 'https://github.com/'
GITHUB_REPO_NAME = '/Ansible'
GITHUB_ANS_REPO =  GITHUB_BASE_URL + GITHUB_USERNAME + GITHUB_REPO_NAME
FILE_NAME = 'ansiblebase.template'

ansible_pull_cmd = "/usr/local/bin/ansible-pull -U {} {}.yml -i localhost".format(
	GITHUB_ANS_REPO,
	APP_NAME
)

public_cidr_ip = str(ip_network(get_ip())) #Classless Inter-Domain Routing IP (CidrIp)

t = Template()

t.add_description("Effective DevOps in AWS: HelloHell Web Application")

t.add_parameter(Parameter(
	"KeyPair",
	Description="Name od an existing EC2 KeyPair to SSH",
	Type="AWS::EC2::KeyPair::KeyName",
	ConstraintDescription="Must be the name of an existing EC2 KeyPair.",
))

t.add_resource(ec2.SecurityGroup(
	"SecurityGroup",	
	GroupDescription="Allow SSH and TCP/{} access".format(APP_PORT),
	SecurityGroupIngress=[
		ec2.SecurityGroupRule( #SSH connection
			IpProtocol="tcp",
			FromPort="22",
			ToPort="22",
			CidrIp=public_cidr_ip, # Connect from the local IP
		),
		ec2.SecurityGroupRule( #TCP connection
			IpProtocol="tcp",
			FromPort=APP_PORT,
			ToPort=APP_PORT,
			CidrIp="0.0.0.0/0",
		),
	],
))

ud = Base64(Join('\n', [
    "#!/bin/bash",
    "yum install --enablerepo=epel -y git",
    "pip install ansible",
    ansible_pull_cmd,
    "echo '*/10 * * * * {}' > /etc/cron.d/ansible-pull".format(ansible_pull_cmd)
   ]))

t.add_resource(Role(
	"Role",
	AssumeRolePolicyDocument=Policy(
		Statement = [
			Statement(
				Effect = Allow,
				Action = [AssumeRole],
				Principal = Principal("Service", ["ec2.amazonaws.com"])
			)
		]
	)
))

t.add_resource(InstanceProfile(
	"InstanceProfile",
	Path="/",
	Roles=[Ref("Role")],
))

t.add_resource(ec2.Instance(
	"instance",
	ImageId="ami-40142d25",
	InstanceType="t2.micro",
	SecurityGroups=[Ref("SecurityGroup")],
	KeyName=Ref("KeyPair"),
	UserData=ud,
	IamInstanceProfile=Ref("InstanceProfile"),
))

t.add_output(Output(
	"InstancePublicIp",
	Description="Public IP of our instance.",
	Value=GetAtt("instance", "PublicIp"),
))

t.add_output(Output(
	"WebUrl",
	Description="Application Endpoint",
	Value=Join("", [
		"http://", GetAtt("instance", "PublicDnsName"),
		":", APP_PORT,
	]),
))

with open(FILE_NAME, 'w+') as f:
	f.write(t.to_json())
f.close()
