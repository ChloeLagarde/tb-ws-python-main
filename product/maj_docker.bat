chcp 1252

set "api_path= %~dpnx0"
set "api_path=%api_path:~0,-14%"

cd %api_path%
docker stop container_api
docker rm container_api
docker image rm api
docker build -t api .
docker run -d -p 5000:5000 --name container_api api

