{% import_json tpldir + "/env_vars_cicd.json" as envs %}
{% set destination_path = '/opt/'~envs['SERVICE_NAME'] %}

docker-compose_down:
  cmd.run:
    - name: docker-compose -f {{ destination_path }}/docker-compose.yml down

docker_prune:
  cmd.run:
    - name: docker image prune -f
    - require:
      - cmd: docker-compose_down

makedirs:
  file.absent:
    - name: {{ destination_path }}
    - require:
      - cmd: docker-compose_down

consul_file:
  file.absent:
    - name: /opt/consul.d/{{ envs['SERVICE_NAME'] }}.hcl

consul_reload:
  cmd.run:
    - name: consul reload
    - require:
      - file: consul_file
