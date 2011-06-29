# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack, LLC
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Functional test case that utilizes httplib2 against the API server"""

import hashlib
import httplib2
import json
import os
from pprint import pprint

from tests import functional
from tests.utils import execute

FIVE_KB = 5 * 1024
FIVE_GB = 5 * 1024 * 1024 * 1024


class TestApiHttplib2(functional.FunctionalTest):

    """Functional tests using httplib2 against the API server"""

    def test_001_get_head_simple_post(self):
        """
        We test the following sequential series of actions:

        0. GET /images
        - Verify no public images
        1. GET /images/detail
        - Verify no public images
        2. HEAD /images/1
        - Verify 404 returned
        3. POST /images with public image named Image1 with a location
        attribute and no custom properties
        - Verify 201 returned
        4. HEAD /images/1
        - Verify HTTP headers have correct information we just added
        5. GET /images/1
        - Verify all information on image we just added is correct
        6. GET /images
        - Verify the image we just added is returned
        7. GET /images/detail
        - Verify the image we just added is returned
        8. PUT /images/1 with custom properties of "distro" and "arch"
        - Verify 200 returned
        9. GET /images/1
        - Verify updated information about image was stored
        10. PUT /images/1
        - Remove a previously existing property.
        11. PUT /images/1
        - Add a previously deleted property.
        """

        self.cleanup()
        self.start_servers()

        # 0. GET /images
        # Verify no public images
        path = "http://%s:%d/v1/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)
        self.assertEqual(content, '{"images": []}')

        # 1. GET /images/detail
        # Verify no public images
        path = "http://%s:%d/v1/images/detail" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)
        self.assertEqual(content, '{"images": []}')

        # 2. HEAD /images/1
        # Verify 404 returned
        path = "http://%s:%d/v1/images/1" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'HEAD')
        self.assertEqual(response.status, 404)

        # 3. POST /images with public image named Image1
        # attribute and no custom properties. Verify a 200 OK is returned
        image_data = "*" * FIVE_KB
        headers = {'Content-Type': 'application/octet-stream',
                   'X-Image-Meta-Name': 'Image1',
                   'X-Image-Meta-Is-Public': 'True'}
        path = "http://%s:%d/v1/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'POST', headers=headers,
                                         body=image_data)
        self.assertEqual(response.status, 201)
        data = json.loads(content)
        self.assertEqual(data['image']['checksum'],
                         hashlib.md5(image_data).hexdigest())
        self.assertEqual(data['image']['size'], FIVE_KB)
        self.assertEqual(data['image']['name'], "Image1")
        self.assertEqual(data['image']['is_public'], True)

        # 4. HEAD /images/1
        # Verify image found now
        path = "http://%s:%d/v1/images/1" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'HEAD')
        self.assertEqual(response.status, 200)
        self.assertEqual(response['x-image-meta-name'], "Image1")

        # 5. GET /images/1
        # Verify all information on image we just added is correct
        path = "http://%s:%d/v1/images/1" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)

        expected_image_headers = {
            'x-image-meta-id': '1',
            'x-image-meta-name': 'Image1',
            'x-image-meta-is_public': 'True',
            'x-image-meta-status': 'active',
            'x-image-meta-disk_format': '',
            'x-image-meta-container_format': '',
            'x-image-meta-size': str(FIVE_KB),
            'x-image-meta-location': 'file://%s/1' % self.api_server.image_dir}

        expected_std_headers = {
            'content-length': str(FIVE_KB),
            'content-type': 'application/octet-stream'}

        for expected_key, expected_value in expected_image_headers.items():
            self.assertEqual(response[expected_key], expected_value,
                            "For key '%s' expected header value '%s'. Got '%s'"
                            % (expected_key, expected_value,
                               response[expected_key]))

        for expected_key, expected_value in expected_std_headers.items():
            self.assertEqual(response[expected_key], expected_value,
                            "For key '%s' expected header value '%s'. Got '%s'"
                            % (expected_key,
                               expected_value,
                               response[expected_key]))

        self.assertEqual(content, "*" * FIVE_KB)
        self.assertEqual(hashlib.md5(content).hexdigest(),
                         hashlib.md5("*" * FIVE_KB).hexdigest())

        # 6. GET /images
        # Verify no public images
        path = "http://%s:%d/v1/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)

        expected_result = {"images": [
            {"container_format": None,
             "disk_format": None,
             "id": 1,
             "name": "Image1",
             "checksum": "c2e5db72bd7fd153f53ede5da5a06de3",
             "size": 5120}]}
        self.assertEqual(json.loads(content), expected_result)

        # 7. GET /images/detail
        # Verify image and all its metadata
        path = "http://%s:%d/v1/images/detail" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)

        expected_image = {
            "status": "active",
            "name": "Image1",
            "deleted": False,
            "container_format": None,
            "disk_format": None,
            "id": 1,
            "location": "file://%s/1" % self.api_server.image_dir,
            "is_public": True,
            "deleted_at": None,
            "properties": {},
            "size": 5120}

        image = json.loads(content)

        for expected_key, expected_value in expected_image.items():
            self.assertEqual(expected_value, expected_image[expected_key],
                            "For key '%s' expected header value '%s'. Got '%s'"
                            % (expected_key,
                               expected_value,
                               image['images'][0][expected_key]))

        # 8. PUT /images/1 with custom properties of "distro" and "arch"
        # Verify 200 returned
        headers = {'X-Image-Meta-Property-Distro': 'Ubuntu',
                   'X-Image-Meta-Property-Arch': 'x86_64'}
        path = "http://%s:%d/v1/images/1" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'PUT', headers=headers)
        self.assertEqual(response.status, 200)
        data = json.loads(content)
        self.assertEqual(data['image']['properties']['arch'], "x86_64")
        self.assertEqual(data['image']['properties']['distro'], "Ubuntu")

        # 9. GET /images/detail
        # Verify image and all its metadata
        path = "http://%s:%d/v1/images/detail" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)

        expected_image = {
            "status": "active",
            "name": "Image1",
            "deleted": False,
            "container_format": None,
            "disk_format": None,
            "id": 1,
            "location": "file://%s/1" % self.api_server.image_dir,
            "is_public": True,
            "deleted_at": None,
            "properties": {'distro': 'Ubuntu', 'arch': 'x86_64'},
            "size": 5120}

        image = json.loads(content)

        for expected_key, expected_value in expected_image.items():
            self.assertEqual(expected_value, expected_image[expected_key],
                            "For key '%s' expected header value '%s'. Got '%s'"
                            % (expected_key,
                               expected_value,
                               image['images'][0][expected_key]))

        # 10. PUT /images/1 and remove a previously existing property.
        headers = {'X-Image-Meta-Property-Arch': 'x86_64'}
        path = "http://%s:%d/v1/images/1" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'PUT', headers=headers)
        self.assertEqual(response.status, 200)

        path = "http://%s:%d/v1/images/detail" % ("0.0.0.0", self.api_port)
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)
        data = json.loads(content)['images'][0]
        self.assertEqual(len(data['properties']), 1)
        self.assertEqual(data['properties']['arch'], "x86_64")

        # 11. PUT /images/1 and add a previously deleted property.
        headers = {'X-Image-Meta-Property-Distro': 'Ubuntu',
                   'X-Image-Meta-Property-Arch': 'x86_64'}
        path = "http://%s:%d/v1/images/1" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'PUT', headers=headers)
        self.assertEqual(response.status, 200)
        data = json.loads(content)

        path = "http://%s:%d/v1/images/detail" % ("0.0.0.0", self.api_port)
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)
        data = json.loads(content)['images'][0]
        self.assertEqual(len(data['properties']), 2)
        self.assertEqual(data['properties']['arch'], "x86_64")
        self.assertEqual(data['properties']['distro'], "Ubuntu")

        self.stop_servers()

    def  test_002_queued_process_flow(self):
        """
        We test the process flow where a user registers an image
        with Glance but does not immediately upload an image file.
        Later, the user uploads an image file using a PUT operation.
        We track the changing of image status throughout this process.

        0. GET /images
        - Verify no public images
        1. POST /images with public image named Image1 with no location
           attribute and no image data.
        - Verify 201 returned
        2. GET /images
        - Verify one public image
        3. HEAD /images/1
        - Verify image now in queued status
        4. PUT /images/1 with image data
        - Verify 200 returned
        5. HEAD /images/1
        - Verify image now in active status
        6. GET /images
        - Verify one public image
        """

        self.cleanup()
        self.start_servers()

        # 0. GET /images
        # Verify no public images
        path = "http://%s:%d/v1/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)
        self.assertEqual(content, '{"images": []}')

        # 1. POST /images with public image named Image1
        # with no location or image data
        headers = {'Content-Type': 'application/octet-stream',
                   'X-Image-Meta-Name': 'Image1',
                   'X-Image-Meta-Is-Public': 'True'}
        path = "http://%s:%d/v1/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'POST', headers=headers)
        self.assertEqual(response.status, 201)
        data = json.loads(content)
        self.assertEqual(data['image']['checksum'], None)
        self.assertEqual(data['image']['size'], 0)
        self.assertEqual(data['image']['container_format'], None)
        self.assertEqual(data['image']['disk_format'], None)
        self.assertEqual(data['image']['name'], "Image1")
        self.assertEqual(data['image']['is_public'], True)

        # 2. GET /images
        # Verify 1 public image
        path = "http://%s:%d/v1/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)
        data = json.loads(content)
        self.assertEqual(data['images'][0]['id'], 1)
        self.assertEqual(data['images'][0]['checksum'], None)
        self.assertEqual(data['images'][0]['size'], 0)
        self.assertEqual(data['images'][0]['container_format'], None)
        self.assertEqual(data['images'][0]['disk_format'], None)
        self.assertEqual(data['images'][0]['name'], "Image1")

        # 3. HEAD /images
        # Verify status is in queued
        path = "http://%s:%d/v1/images/1" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'HEAD')
        self.assertEqual(response.status, 200)
        self.assertEqual(response['x-image-meta-name'], "Image1")
        self.assertEqual(response['x-image-meta-status'], "queued")
        self.assertEqual(response['x-image-meta-size'], '0')
        self.assertEqual(response['x-image-meta-id'], '1')

        # 4. PUT /images/1 with image data, verify 200 returned
        image_data = "*" * FIVE_KB
        headers = {'Content-Type': 'application/octet-stream'}
        path = "http://%s:%d/v1/images/1" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'PUT', headers=headers,
                                         body=image_data)
        self.assertEqual(response.status, 200)
        data = json.loads(content)
        self.assertEqual(data['image']['checksum'],
                         hashlib.md5(image_data).hexdigest())
        self.assertEqual(data['image']['size'], FIVE_KB)
        self.assertEqual(data['image']['name'], "Image1")
        self.assertEqual(data['image']['is_public'], True)

        # 5. HEAD /images
        # Verify status is in active
        path = "http://%s:%d/v1/images/1" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'HEAD')
        self.assertEqual(response.status, 200)
        self.assertEqual(response['x-image-meta-name'], "Image1")
        self.assertEqual(response['x-image-meta-status'], "active")

        # 6. GET /images
        # Verify 1 public image still...
        path = "http://%s:%d/v1/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)
        data = json.loads(content)
        self.assertEqual(data['images'][0]['checksum'],
                         hashlib.md5(image_data).hexdigest())
        self.assertEqual(data['images'][0]['id'], 1)
        self.assertEqual(data['images'][0]['size'], FIVE_KB)
        self.assertEqual(data['images'][0]['container_format'], None)
        self.assertEqual(data['images'][0]['disk_format'], None)
        self.assertEqual(data['images'][0]['name'], "Image1")

        self.stop_servers()

    def test_003_version_variations(self):
        """
        We test that various calls to the images and root endpoints are
        handled properly, and that usage of the Accept: header does
        content negotiation properly.
        """

        self.cleanup()
        self.start_servers()

        versions = {'versions': [{
            "id": "v1.0",
            "status": "CURRENT",
            "links": [{
                "rel": "self",
                "href": "http://0.0.0.0:%d/v1/" % self.api_port}]}]}
        versions_json = json.dumps(versions)
        images = {'images': []}
        images_json = json.dumps(images)

        def validate_versions(response, content):
            """
            Returns True if supplied response text contains an
            appropriate 300 Multiple Choices and has the correct
            versions output.
            """
            return (response.status == 300
                    and versions_json == content)

        # 0. GET / with no Accept: header
        # Verify version choices returned.
        path = "http://%s:%d/" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        # Have to set Accept header, or else GLANCE returns a 500
        # headers = {'Accept': '*/*'}
        # response, content = http.request(path, 'GET', headers=headers)
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 300)
        self.assertEqual(content, versions_json)

        # 1. GET /images with no Accept: header
        # Verify version choices returned.
        path = "http://%s:%d/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        # Have to set Accept header, or else GLANCE returns a 500
        headers = {'Accept': '*/*'}
        response, content = http.request(path, 'GET', headers=headers)
        self.assertEqual(response.status, 300)
        self.assertEqual(content, versions_json)


        # 2. GET /v1/images with no Accept: header
        # Verify empty images list returned.
        path = "http://%s:%d/v1/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        response, content = http.request(path, 'GET')
        self.assertEqual(response.status, 200)
        self.assertEqual(content, images_json)

        # 3. GET / with Accept: unknown header
        # Verify version choices returned. Verify message in API log about
        # unknown accept header.
        path = "http://%s:%d/" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        headers = {'Accept': 'unknown'}
        response, content = http.request(path, 'GET', headers=headers)
        self.assertEqual(response.status, 300)
        self.assertEqual(content, versions_json)
        self.assertTrue('Unknown accept header'
                        in open(self.api_server.log_file).read())

        # 4. GET / with an Accept: application/vnd.openstack.images-v1
        # Verify empty image list returned
        # path = "http://%s:%d/images" % ("0.0.0.0", self.api_port)
        # http = httplib2.Http()
        # headers = {'Accept': 'application/vnd.openstack.compute-v1'}
        # response, content = http.request(path, 'GET', headers=headers)
        # pprint(response)
        # pprint(content)
        # self.assertEqual(response.status, 200)
        # self.assertEqual(content, images_json)

        # 5. GET /images with a Accept: application/vnd.openstack.compute-v1
        # header. Verify version choices returned. Verify message in API log
        # about unknown accept header.
        path = "http://%s:%d/images" % ("0.0.0.0", self.api_port)
        http = httplib2.Http()
        headers = {'Accept': 'application/vnd.openstack.compute-v1'}
        response, content = http.request(path, 'GET', headers=headers)
        self.assertEqual(response.status, 300)
        self.assertEqual(content, versions_json)
        self.assertTrue('Unknown accept header'
                        in open(self.api_server.log_file).read())
