from agents.header_matcher import HeaderMatcher


class InventoryAgent:

    def __init__(self, knowledge):
        self.matcher = HeaderMatcher(knowledge)


    def analyze(self, columns, instructions=""):

        return {
            "instructions": instructions,
            "mapping": self.matcher.match(columns),
            "ai_rules": self.parse_business_rules(instructions),
        }


    def parse_business_rules(self, instructions):

        text = (instructions or "").lower()

        rules = {}

        if "14k" in text and "500" in text and "1000" in text:
            rules["pricing_rules"] = {
                "type": "metal_based",
                "conditions": [
                    {
                        "match_contains": "14k",
                        "price": 500,
                    },
                    {
                        "default": True,
                        "price": 1000,
                    },
                ],
            }

        return rules
