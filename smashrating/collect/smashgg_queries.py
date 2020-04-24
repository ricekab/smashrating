"""
GraphQL queries in string form used by SmashGGScraper.
"""
TOURNAMENTS_BY_COUNTRY_PAGING = """
query TournamentsByCountryPaging($countryCode: String!, $afterDate: Timestamp!, $perPage: Int!) {
  tournaments(query: {
    perPage: $perPage
    filter: {
      countryCode: $countryCode
      videogameIds: [1386]
      upcoming: false
      hasOnlineEvents: false
      afterDate: $afterDate
    }
  }) {
    pageInfo {
      totalPages
      perPage
    }
  }
}
""".strip()

TOURNAMENTS_BY_COUNTRY = """
query TournamentsByCountry($countryCode: String!, $afterDate: Timestamp!, $page: Int!, $perPage: Int!) {
  tournaments(query: {
    page: $page
    perPage: $perPage
    filter: {
      countryCode: $countryCode
      videogameIds: [1386]
      upcoming: false
      hasOnlineEvents: false
      afterDate: $afterDate
    }
  }) {
    nodes {
      id
      name
      countryCode
      endAt
      events {
        id
        name
        isOnline
        numEntrants
        state
        type
        videogame {
          id
        }
      }
    }
  }
}
""".strip()

TOURNAMENTS_ALL_PAGING = """
query TournamentsPaging($afterDate: Timestamp!, $perPage: Int!) {
  tournaments(query: {
    perPage: $perPage
    filter: {
      videogameIds: [1386]
      upcoming: false
      hasOnlineEvents: false
      afterDate: $afterDate
    }
  }) {
    pageInfo {
      totalPages
      perPage
    }
  }
}
""".strip()

TOURNAMENTS_ALL = """
query TournamentsAll($afterDate: Timestamp!, $page: Int!, $perPage: Int!) {
  tournaments(query: {
    page: $page
    perPage: $perPage
    filter: {
      videogameIds: [1386]
      upcoming: false
      hasOnlineEvents: false
      afterDate: $afterDate
    }
  }) {
    nodes {
      id
      name
      countryCode
      endAt
      events {
        id
        name
        isOnline
        numEntrants
        state
        type
        videogame {
          id
        }
      }
    }
  }
}
""".strip()

EVENT_SETS_PAGING = """
query EventSets($eventId: ID!, $perPage: Int!) {
  event(id: $eventId) {
    id
    name
    sets(
      perPage: $perPage
      sortType: CALL_ORDER
    ) {
      pageInfo {
        totalPages
      }
    }
  }
}
""".strip()

EVENT_SETS = """
query EventSets($eventId: ID!, $page: Int!, $perPage: Int!) {
  event(id: $eventId) {
    sets(
      page: $page
      perPage: $perPage
      sortType: CALL_ORDER
    ) {
      nodes {
        id
        startedAt
        slots {
          standing {
            placement
            stats {
              score {
                value
              }
            }
          }
          entrant {
            participants {
              gamerTag
              user {
                id
              }
              verified
            }
          }
        }
      }
    }
  }
}
""".strip()
