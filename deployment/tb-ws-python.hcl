services {
  name = "{{ SERVICE_NAME }}"
  port = {{ DOCKER_PORT }}

  tags = [
    "traefik.enable=true",
    "traefik.http.routers.{{ SERVICE_NAME }}.tls=true",
    "traefik.http.routers.{{ SERVICE_NAME }}.entrypoints=websecure",
    "traefik.http.routers.{{ SERVICE_NAME }}.rule=Host(`{{ ENVIRONMENT_URL }}`)",

    "disableAlerting"
  ]

  checks = [
    {
      name = "TCP Check"
      tcp = "127.0.0.1:{{ DOCKER_PORT }}"
      interval = "1s"
      timeout = "900ms"
      failures_before_critical = 3
    },
    {
      name = "HTTP Check"
      http = "http://127.0.0.1:{{ DOCKER_PORT }}/"
      interval = "1s"
      timeout = "900ms"
      failures_before_critical = 3
    }
  ]
}
