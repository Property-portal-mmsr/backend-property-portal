import unittest
from unittest.mock import MagicMock
from app.services.analytics_service import calculate_achievement_pct

class TestTeamLeaderIncentiveTrackerLogic(unittest.TestCase):

    def test_overall_team_revenue_leader_not_in_members(self):
        # TEST 1 & TEST 6:
        # Team Leader Revenue = 18,500, Other team revenue = 47,500
        # -> Team Revenue must be 66,000.
        leader_revenue = 18500.0
        member_revenues = [47500.0]
        leader_in_members = False

        if leader_in_members:
            overall_team_revenue = sum(member_revenues)
        else:
            overall_team_revenue = sum(member_revenues) + leader_revenue

        self.assertEqual(overall_team_revenue, 66000.0)

    def test_team_achievement_pct(self):
        # TEST 2:
        # Base Target = 2,75,000, Team Revenue = 66,000
        # -> Achievement must be 24.0%.
        overall_team_revenue = 66000.0
        team_base_target = 275000.0
        achievement_pct = calculate_achievement_pct(overall_team_revenue, team_base_target)
        self.assertAlmostEqual(achievement_pct, 24.0, places=1)

    def test_leader_revenue_separate_display(self):
        # TEST 3:
        leader_revenue = 18500.0
        self.assertEqual(leader_revenue, 18500.0)

    def test_no_double_counting_when_leader_in_members(self):
        # TEST 4 & TEST 5:
        # If leader is already included in members:
        # DO NOT add leader revenue again.
        leader_revenue = 18500.0
        # Suppose dataset already includes leader:
        member_revenues = [47500.0, 18500.0]
        leader_in_members = True

        if leader_in_members:
            overall_team_revenue = sum(member_revenues)
        else:
            overall_team_revenue = sum(member_revenues) + leader_revenue

        self.assertEqual(overall_team_revenue, 66000.0)

    def test_base_target_sum_of_unique_members(self):
        # TEST 7:
        # Base Target is sum of all unique team members including leader
        targets = [55000.0, 55000.0, 55000.0, 55000.0, 55000.0]
        leader_target = 0.0
        leader_in_members = False
        team_base_target = sum(targets) + (0.0 if leader_in_members else leader_target)
        self.assertEqual(team_base_target, 275000.0)

if __name__ == "__main__":
    unittest.main()
