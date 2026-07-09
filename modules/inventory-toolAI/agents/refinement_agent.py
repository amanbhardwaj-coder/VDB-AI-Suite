class RefinementAgent:

    def normalize(self, value):

        if value is None:
            return ""

        value = str(value)
        value = value.replace("#", ",")
        value = value.replace("|", ",")
        value = value.replace(";", ",")

        values = []

        for item in value.split(","):
            item = item.strip()

            if item and item not in values:
                values.append(item)

        return ",".join(values)
