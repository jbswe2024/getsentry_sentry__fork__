from sentry.models.apiapplication import ApiApplication
from sentry.models.apiauthorization import ApiAuthorization
from sentry.models.apitoken import ApiToken
from sentry.testutils.cases import APITestCase
from sentry.testutils.silo import control_silo_test


class ApiAuthorizationsTest(APITestCase):
    endpoint = "sentry-api-0-api-authorizations"

    def setUp(self):
        super().setUp()
        self.login_as(self.user)


@control_silo_test
class ApiAuthorizationsListTest(ApiAuthorizationsTest):
    def test_simple(self):
        app = ApiApplication.objects.create(name="test", owner=self.user)
        auth = ApiAuthorization.objects.create(application=app, user=self.user)
        ApiAuthorization.objects.create(
            application=app, user=self.create_user("example@example.com")
        )

        response = self.get_success_response()
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(auth.id)
        assert response.data[0]["organization"] is None

    def test_org_level_auth(self):
        org = self.create_organization(owner=self.user, slug="test-org-slug")
        app = ApiApplication.objects.create(
            name="test", owner=self.user, requires_org_level_access=True
        )
        ApiAuthorization.objects.create(application=app, user=self.user, organization_id=org.id)

        response = self.get_success_response()
        assert len(response.data) == 1
        assert response.data[0]["organization"]["slug"] == org.slug


@control_silo_test
class ApiAuthorizationsDeleteTest(ApiAuthorizationsTest):
    method = "delete"

    def test_simple(self):
        app = ApiApplication.objects.create(name="test", owner=self.user)
        auth = ApiAuthorization.objects.create(application=app, user=self.user)
        token = ApiToken.objects.create(application=app, user=self.user)

        self.get_success_response(authorization=auth.id, status_code=204)
        assert not ApiAuthorization.objects.filter(id=auth.id).exists()
        assert not ApiToken.objects.filter(id=token.id).exists()

    def test_with_org(self):
        org1 = self.organization
        org2 = self.create_organization(owner=self.user, slug="test-org-2")
        app_with_org = ApiApplication.objects.create(
            name="test-app", owner=self.user, requires_org_level_access=True
        )
        org1_auth = ApiAuthorization.objects.create(
            application=app_with_org, user=self.user, organization_id=org1.id
        )
        org2_auth = ApiAuthorization.objects.create(
            application=app_with_org, user=self.user, organization_id=org2.id
        )
        org1_token = ApiToken.objects.create(
            application=app_with_org, user=self.user, scoping_organization_id=org1.id
        )
        org2_token = ApiToken.objects.create(
            application=app_with_org, user=self.user, scoping_organization_id=org2.id
        )

        self.get_success_response(authorization=org1_auth.id, status_code=204)
        assert not ApiAuthorization.objects.filter(id=org1_auth.id).exists()
        assert not ApiToken.objects.filter(id=org1_token.id).exists()

        assert ApiAuthorization.objects.filter(id=org2_auth.id).exists()
        assert ApiToken.objects.filter(id=org2_token.id).exists()
