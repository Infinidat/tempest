# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import hashlib
import hmac
import time
from urllib import parse as urlparse

from tempest.api.object_storage import base
from tempest.common import utils
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc


class ObjectTempUrlNegativeTest(base.BaseObjectTest):
    """Negative tests of object temp url"""

    metadata = {}
    containers = []

    @classmethod
    def resource_setup(cls):
        super(ObjectTempUrlNegativeTest, cls).resource_setup()

        cls.container_name = cls.create_container()

        # update account metadata
        cls.key = 'Meta'
        cls.metadata = {'Temp-URL-Key': cls.key}
        cls.account_client.create_update_or_delete_account_metadata(
            create_update_metadata=cls.metadata)
        cls.account_client_metadata, _ = \
            cls.account_client.list_account_metadata()

    @classmethod
    def resource_cleanup(cls):
        cls.account_client.create_update_or_delete_account_metadata(
            delete_metadata=cls.metadata)

        cls.delete_containers()

        super(ObjectTempUrlNegativeTest, cls).resource_cleanup()

    def setUp(self):
        super(ObjectTempUrlNegativeTest, self).setUp()
        # make sure the metadata has been set
        self.assertIn('x-account-meta-temp-url-key',
                      self.account_client_metadata)

        self.assertEqual(
            self.account_client_metadata['x-account-meta-temp-url-key'],
            self.key)

        # create object
        self.object_name = data_utils.rand_name(name='ObjectTemp')
        content = data_utils.arbitrary_string(size=len(self.object_name),
                                              base_text=self.object_name)
        self.object_client.create_object(self.container_name,
                                         self.object_name, content)

    def _get_expiry_date(self, expiration_time=1000):
        return int(time.time() + expiration_time)

    def _get_temp_url(self, container, object_name, method, expires,
                      key):
        """Create the temporary URL."""

        path = "%s/%s/%s" % (
            urlparse.urlparse(self.object_client.base_url).path,
            container, object_name)

        hmac_body = '%s\n%s\n%s' % (method, expires, path)
        sig = hmac.new(
            key.encode(), hmac_body.encode(), hashlib.sha256
        ).hexdigest()

        url = "%s/%s?temp_url_sig=%s&temp_url_expires=%s" % (container,
                                                             object_name,
                                                             sig, expires)

        return url

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('5a583aca-c804-41ba-9d9a-e7be132bdf0b')
    @utils.requires_ext(extension='tempurl', service='object')
    def test_get_object_after_expiration_time(self):
        """Test getting object after expiration time"""
        expires = self._get_expiry_date(1)
        # get a temp URL for the created object
        url = self._get_temp_url(self.container_name,
                                 self.object_name, "GET",
                                 expires, self.key)

        # temp URL is valid for 1 seconds, let's wait 2
        time.sleep(2)

        self.assertRaises(lib_exc.Unauthorized,
                          self.object_client.get, url)
