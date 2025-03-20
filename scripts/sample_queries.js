//Percentile Query to show whether Christmas power usage is unusual compared to normal days
db.power_readings.aggregate([
  // Match December data
  {
    $match: {
      timestamp: {
        $gte: ISODate("2024-12-01T00:00:00Z"),
        $lt: ISODate("2025-01-01T00:00:00Z")
      },
      "device_id.Category": "Appliance"  // Focus on one category for clarity
    }
  },
  // Use percentile operator to analyze power consumption
  {
    $group: {
      _id: null,
      regularDays: {
        $percentile: {
          input: "$current_power",
          p: [0.5, 0.95],  // Median and 95th percentile
          method: "approximate"
        }
      },
      // Calculate Christmas day separately for comparison
      christmasDay: {
        $push: {
          $cond: [
            { $and: [
              { $gte: ["$timestamp", ISODate("2024-12-25T00:00:00Z")] },
              { $lt: ["$timestamp", ISODate("2024-12-26T00:00:00Z")] }
            ]},
            "$current_power",
            null
          ]
        }
      }
    }
  },
  // Format for display
  {
    $project: {
      _id: 0,
      medianPower: { $arrayElemAt: ["$regularDays", 0] },
      "95thPercentilePower": { $arrayElemAt: ["$regularDays", 1] },
      christmasPower: { $avg: { $filter: { input: "$christmasDay", as: "power", cond: { $ne: ["$$power", null] } } } }
    }
  }
])
