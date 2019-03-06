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

ApplicationPort = "3000"
PublicCidrIp = str(ip_network(get_ip())) #Classless Inter-Domain Routing IP (CidrIp)

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
	GroupDescription="Allow SSH and TCP/{} access".format(ApplicationPort),
	SecurityGroupIngress=[
		ec2.SecurityGroupRule( #SSH connection
			IpProtocol="tcp",
			FromPort="22",
			ToPort="22",
			CidrIp=PublicCidrIp, #connect from the local IP
		),
		ec2.SecurityGroupRule( #TCP connection
			IpProtocol="tcp",
			FromPort=ApplicationPort,
			ToPort=ApplicationPort,
			CidrIp="0.0.0.0/0",
		),
	],
))

ud = Base64(Join('\n', [
	"#!/bin/bash",
	"sudo yum install --enablerepo=epel -y nodejs",
	"wget http://bit.ly/2vESNuc -O /home/ec2-user/helloworld.js",
	"wget http://bit.ly/2vVvT18 -O /etc/init/helloworld.conf",
	"start helloworld",
]))

t.add_resource(ec2.Instance(
	"instance",
	ImageId="ami-40142d25",
	InstanceType="t2.micro",
	SecurityGroups=[Ref("SecurityGroup")],
	KeyName=Ref("KeyPair"),
	UserData=ud,
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
		":", ApplicationPort,
	]),
))

print t.to_json()
