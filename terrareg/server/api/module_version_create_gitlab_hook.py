
import hashlib
import re
from hmac import compare_digest

from flask import request

from terrareg.server.error_catching_resource import ErrorCatchingResource
import terrareg.database
import terrareg.config
import terrareg.models
import terrareg.module_extractor
import terrareg.errors


class ApiModuleVersionCreateGitLabHook(ErrorCatchingResource):
    """Provide interface for GitLab hook to detect new and changed releases."""

    def _post(self, namespace, name, provider):
        """Create, update or delete new version based on GitLab release hooks."""
        with terrareg.database.Database.start_transaction() as transaction_context:
            _, _, module_provider, error = self.get_module_provider_by_names(namespace, name, provider)
            if error:
                return error

            # Validate signature
            if terrareg.config.Config().UPLOAD_API_KEYS:
                # Get signature from request
                request_signature = request.headers.get('X-Gitlab-Token', '')
                # Iterate through each of the keys and test
                for test_key in terrareg.config.Config().UPLOAD_API_KEYS:
                    # If the signatures match, break from loop
                    if compare_digest(test_key, request_signature):
                        break
                # If a valid signature wasn't found with one of the configured keys,
                # return 401
                else:
                    return self._get_401_response()

            if not module_provider.get_git_clone_url():
                return {'status': 'Error', 'message': 'Module provider is not configured with a repository'}, 400

            if request.headers.get('X-Gitlab-Event', '') != 'Release Hook':
                return {'status': 'Error', 'message': 'Received a non-release hook request'}, 400
            
            gitlab_data = request.json
    
            # Obtain tag name
            tag_ref = gitlab_data.get('tag')
            if not tag_ref:
                return {'status': 'Error', 'message': 'tag not present in request'}, 400

            # Attempt to match version against regex
            version = module_provider.get_version_from_tag(tag_ref)

            if not version:
                return {'status': 'Error', 'message': 'Release tag does not match configured version regex'}, 400

            # Create module version
            module_version = terrareg.models.ModuleVersion(module_provider=module_provider, version=version)

            action = gitlab_data.get('action')
            if not action:
                return {"status": "Error", "message": "No action present in request"}, 400

            if action == 'delete':
                if not terrareg.config.Config().UPLOAD_API_KEYS:
                    return {
                        'status': 'Error',
                        'message': 'Version deletion requires API key authentication',
                        'tag': tag_ref
                    }, 400
                module_version.delete()

                return {
                    'status': 'Success'
                }
            else:
                # Perform import from git
                try:
                    with module_version.module_create_extraction_wrapper():
                        with terrareg.module_extractor.GitModuleExtractor(module_version=module_version) as me:
                            me.process_upload()

                except terrareg.errors.TerraregError as exc:
                    # Roll back creation of module version
                    transaction_context.transaction.rollback()

                    return {
                        'status': 'Error',
                        'message': f'Tag failed to import: {str(exc)}',
                        'tag': tag_ref
                    }, 500
                else:
                    return {
                        'status': 'Success',
                        'message': 'Imported provided tag',
                        'tag': tag_ref
                    }
