# Start the services
up:
	docker-compose -f docker-compose.yml up -d --build

login:
	aws sso login
	aws codeartifact login --tool pip --domain mydata --domain-owner 381492142849 --region eu-west-1 --repository Development 

#build docker image
build:
	docker build --no-cache --secret id=pip,src="${HOME}/.config/pip/pip.conf" . -t bcx_notfications

# Stop the services
down:
	docker-compose -f docker-compose.yml down

lint:
	hatch run lint:isort ./src/*
	hatch run lint:black ./src/*
	hatch run lint:pylint src/*

run:
	docker exec bcx_notfications-bcx-1 bash -c "python main.py --bucket 'matteo-test-bucket-1234-5678-9123' --key 'bcx/CreditBureau_D_ITC_20250211_060518-KGEBTTSN4BBX.csv'"
# docker exec bcx_notfications-bcx-1 bash -c "python main.py --bucket 'matteo-test-bucket-1234-5678-9123' --key 'bcx/CreditBureau_D_ITC_20260424_060518.csv'"
# docker exec bcx_notfications-bcx-1 bash -c "python main.py --bucket 'matteo-test-bucket-1234-5678-9123' --key 'bcx/CreditBureau_D_ITC_20250424060518.csv'"
# docker exec bcx_notfications-bcx-1 bash -c "python main.py --bucket 'matteo-test-bucket-1234-5678-9123' --key 'bcx/CreditBureau_D_ITC_250224_060518.csv'"
