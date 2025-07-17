login:
	aws sso login
	aws codeartifact login --tool pip --domain mydata --domain-owner 381492142849 --region eu-west-1 --repository Development 

lint:
	hatch run lint:isort ./src/*
	hatch run lint:black ./src/*
	hatch run lint:pylint src/*

