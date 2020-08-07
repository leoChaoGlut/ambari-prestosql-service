# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os.path as path
import uuid

from common import create_connectors, delete_connectors, launcherPath, etcDir, catalogDir, PRESTO_TAR_NAME, \
    PRESTO_TAR_URL, prestoHome, jdk11Url, jdk11Home, jdk11TarName, exportJavaHomeAndPath
from resource_management.core.exceptions import ExecutionFailed, ComponentIsNotRunning
from resource_management.core.resources.system import Execute
from resource_management.libraries.script.script import Script


class Worker(Script):
    def install(self, env):
        # download jdk11 and extract jdk11 tarball
        tmpJdk11Path = '/tmp/' + jdk11TarName
        Execute('mkdir -p {0}'.format(jdk11Home))
        Execute('wget --no-check-certificate {0} -O {1}'.format(jdk11Url, tmpJdk11Path))
        Execute('tar -xf {0} -C {1} --strip-components=1'.format(tmpJdk11Path, jdk11Home))

        # download and extract presto tarball
        Execute('mkdir -p {0}'.format(catalogDir))
        tmpPrestoTarballPath = '/tmp/' + PRESTO_TAR_NAME
        Execute('wget --no-check-certificate {0} -O {1}'.format(PRESTO_TAR_URL, tmpPrestoTarballPath))
        Execute('tar -xf {0} -C {1} --strip-components=1'.format(tmpPrestoTarballPath, prestoHome))

        self.configure(env)

    def stop(self, env):
        Execute(exportJavaHomeAndPath + ' && {0} stop'.format(launcherPath))

    def start(self, env):
        self.configure(self)
        Execute(exportJavaHomeAndPath + ' && {0} start'.format(launcherPath))

    def status(self, env):
        try:
            Execute(exportJavaHomeAndPath + ' && {0} status'.format(launcherPath))
        except ExecutionFailed as ef:
            if ef.code == 3:
                raise ComponentIsNotRunning("ComponentIsNotRunning")
            else:
                raise ef

    def configure(self, env):
        from params import node_properties, jvm_config, config_properties, connectors_to_add, connectors_to_delete
        key_val_template = '{0}={1}\n'

        with open(path.join(etcDir, 'node.properties'), 'w') as f:
            for key, value in node_properties.iteritems():
                f.write(key_val_template.format(key, value))
            f.write(key_val_template.format('node.id', str(uuid.uuid4())))

        with open(path.join(etcDir, 'jvm.config'), 'w') as f:
            f.write(jvm_config['jvm.config'])

        with open(path.join(etcDir, 'config.properties'), 'w') as f:
            for key, value in config_properties.iteritems():
                f.write(key_val_template.format(key, value))
            f.write(key_val_template.format('coordinator', 'false'))

        create_connectors(connectors_to_add)
        delete_connectors(connectors_to_delete)
        create_connectors("{'tpch': ['connector.name=tpch']}")


if __name__ == '__main__':
    Worker().execute()
