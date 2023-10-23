from flask import url_for


class NavBar:
    sections: list
    route_map: dict

    def __init__(self):
        self.sections = []
        self.route_map = {}

    def add_section(self, label, route):
        self.sections.append(NavBarSection(label, route, self))

    def map_route(self, route, label):
        self.route_map[route] = label


class NavBarSection:
    label: str
    route: str
    nav_bar: NavBar

    def __init__(self, label, route, nav_bar):
        self.label = label  # Navigation link text
        self.route = route  # Route ("transfer.index" for example)
        self.nav_bar = nav_bar  # Parent NavBar (Needed to access route map)

    def get_url(self):
        return url_for(self.route)

    def is_active(self, request):
        # Don't check if request isn't for a static asset
        request_rule = request.url_rule

        if request_rule is None:
            return False

        # Check for arbitrary mapping of request route to nav bar section
        if request_rule.endpoint in self.nav_bar.route_map:
            return self.nav_bar.route_map[request_rule.endpoint] == self.label

        request_blueprint = self.blueprint_of(request_rule.endpoint)

        if request_rule.endpoint == self.route:
            # A section's default route has been requested
            return True
        elif not self.blueprint_has_mapped_route(request_blueprint):
            # A route within a section representing an entire Blueprint may have been requested
            section_route_blueprint = self.blueprint_of(self.route)

            # Found Blueprint-level match between section and request
            return request_blueprint == section_route_blueprint

    def blueprint_has_mapped_route(self, blueprint):
        for mapped_route in self.nav_bar.route_map:
            route_map_blueprint = self.blueprint_of(mapped_route)

            if route_map_blueprint == blueprint:
                return True

        return False

    def blueprint_of(self, route):
        return route.split(".")[0]
