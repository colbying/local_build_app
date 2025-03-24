// Compound wildcard indexes
db.users.createIndex({"location.city": 1, "devices.$**": 1})

// Query 1 for Compound wildcard indexes
db.users.find({"location.city": "San Francisco", "devices.brand": "Philips"}, {"email":1})

// Query 2, find all users with a Space Heater device in New York
db.users.find({"location.city": "New York", "devices.deviceType": "Space Heater"}, {"email":1})

// Queryable encryption