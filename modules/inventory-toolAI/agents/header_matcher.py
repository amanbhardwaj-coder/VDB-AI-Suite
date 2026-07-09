import re


def norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


class HeaderMatcher:

    def __init__(self, knowledge):
        self.knowledge = knowledge


    def match(self, columns):

        output = []

        for column in columns:

            best = {
                "vendor_column": column,
                "accepted_header": "",
                "internal_setter": "",
                "confidence": 0,
            }

            for setter, data in self.knowledge.items():

                accepted = data.get("accepted_header", "")
                variations = data.get("variations", [])

                for variation in variations:

                    score = 0
                    c = norm(column)
                    v = norm(variation)

                    if c == v:
                        score = 1
                    elif c and v and (c in v or v in c):
                        score = 0.8

                    if score > best["confidence"]:
                        best = {
                            "vendor_column": column,
                            "accepted_header": accepted,
                            "internal_setter": setter,
                            "confidence": score,
                        }

            output.append(best)

        return output
