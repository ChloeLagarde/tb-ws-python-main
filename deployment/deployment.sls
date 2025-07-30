{% import_json tpldir + "/env_vars_cicd.json" as envs %}
{% set destination_path = '/opt/'~envs['SERVICE_NAME'] %}

makedirs:
  file.directory:
    - name: {{ destination_path }}
    - user : root
    - group: root
    - mode: '0755'
    - makedirs: True

push_compose:
  file.managed:
    - name: {{ destination_path }}/docker-compose.yml
    - user: root
    - group: root
    - mode: '0640'
    - source: salt://{{ tpldir }}/docker-compose.j2
    - backup: minion
    - template: jinja
    - defaults:
      DOCKER_TAG: {{ envs['DOCKER_TAG'] }}
      DOCKER_PORT: 8082
    - require:
      - file: makedirs

docker-compose_up:
  cmd.run:
    - name: docker-compose -f {{ destination_path }}/docker-compose.yml pull && docker-compose -f {{ destination_path }}/docker-compose.yml up -d
    - require:
      - file: push_compose

consul_file:
  file.managed:
    - name: /opt/consul.d/{{ envs['SERVICE_NAME'] }}.hcl
    - user: root
    - group: root
    - mode: '0644'
    - source: salt://{{ tpldir }}/tb-ws-python.hcl
    - backup: minion
    - template: jinja
    - defaults:
      SERVICE_NAME: {{ envs['SERVICE_NAME'] }}
      DOCKER_PORT: 8082
      ENVIRONMENT_URL: {{ envs['ENVIRONMENT_URL'] }}

consul_reload:
  cmd.run:
    - name: consul reload
    - require:
      - file: consul_file
    - onchanges:
      - file: consul_file

