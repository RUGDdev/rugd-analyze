"""Contextual help for the financial intake.

Help text explains a field and shows a worked illustration. It does not supply a
value and it never writes to a field. A sourced benchmark is not produced here:
this module has no benchmark table, and every example is labeled as an
illustration. The only figures computed from the customer's own entries use the
existing seat formula, unchanged.
"""

from __future__ import annotations

from html import escape
from typing import Any

from app.guidance import family_for
from app.inputs import field_state
from engine.financial import seat_occupancy_revenue

BENCHMARK_DEFAULT = (
    "RUGD has not loaded a sourced benchmark for this field. If you want one, ask a trade "
    "association, a Small Business Development Center, your accountant, or your lender. "
    "Record the publication, the date, the geography, and the business size before you rely on it. "
    "A published average is context, not your number."
)
ILLUSTRATION_NOTE = "Illustration only. It is not an average or a benchmark."

DAYS = (
    ("mon", "Mon"),
    ("tue", "Tue"),
    ("wed", "Wed"),
    ("thu", "Thu"),
    ("fri", "Fri"),
    ("sat", "Sat"),
    ("sun", "Sun"),
)
_WEEKEND = {"sat", "sun"}
ASSUMED_WEEKEND_SHARE = 2 / 7

# Each entry: what, why, how, avoid, method, example (family -> text, "general" is the fallback),
# and an optional bench override. The lists are plain language on purpose.
_HELP: dict[str, dict[str, Any]] = {
    "construction_cost": {
        "what": "The one-time cost to build or renovate the space so you can open: walls, floors, plumbing, electrical, and built-in fixtures.",
        "why": "It is usually the largest part of the money needed before the first sale, so it sets how much you must invest or borrow.",
        "how": "Get written quotes from contractors for your actual space. If you only have a range, enter the middle of it and note the range in your notes. Keep equipment, design fees, and permits for their own lines.",
        "avoid": "Counting equipment or permits here and again in their own lines. Copying a cost per square foot from another city. Leaving out the contingency, which has its own line.",
        "method": "Method: add the written quotes for the build. The startup formula needs a number above zero.",
        "example": {
            "hospitality": "A cafe build-out quote of 180000 for walls, plumbing, electrical, hood, and flooring. A separate quote for the espresso machine goes under Equipment.",
            "retail": "A shop fit-out quote of 60000 for shelving, lighting, a counter, and flooring.",
            "software": "A software company may build nothing physical. Enter the real one-time setup spend if there is any, such as office improvements. If there is none, leave the startup build blank and use the monthly figures.",
            "healthcare": "A clinic build-out of 150000 for exam rooms, plumbing, and wiring. Medical equipment goes under Equipment.",
            "services": "An office fit-out of 25000 for partitions, wiring, and furniture built in. If you work from rented space with no build, enter only real setup spend.",
            "general": "A quote of 90000 to prepare the space you will rent. Write down who quoted it and when.",
        },
    },
    "equipment": {
        "what": "Machines, tools, and furniture you buy once and use for years, such as ovens, computers, or chairs.",
        "why": "It adds to the money needed before opening, and it is separate from the build because it can often be leased or bought used.",
        "how": "List each item with a quote or a catalog price, then add them. Decide whether you will buy, finance, or lease, and enter only what you pay before opening.",
        "avoid": "Entering the same oven in both the build quote and here. Counting a lease payment as a one-time cost.",
        "method": "Method: sum of quotes. If you leave it blank RUGD uses 0 for this line.",
        "example": {
            "hospitality": "Espresso machine, grinder, refrigeration, and a dish station quoted at 55000 in total.",
            "retail": "Registers, display fixtures, and a back-room shelving set quoted at 18000.",
            "software": "Laptops and a few monitors for the team, 12000 in total.",
            "healthcare": "Exam tables, a sterilizer, and a computer system quoted at 70000.",
            "services": "Computers, a printer, and desks at 15000.",
            "general": "Everything you will own and use that is not part of the build, added up from quotes.",
        },
    },
    "soft_costs": {
        "what": "One-time costs that are not construction or equipment: design, permits, legal fees, licenses, and insurance during the build.",
        "why": "These are easy to forget and they add up. Leaving them out makes the opening cost look smaller than it is.",
        "how": "Ask your architect, attorney, and insurance agent for estimates. Check your city or county for permit and license fees.",
        "avoid": "Adding pre-opening marketing or opening cash here if you plan to enter them in Pre-opening working capital.",
        "method": "Method: add the fees you expect. If you leave it blank RUGD uses 0 for this line.",
        "example": {
            "hospitality": "Design drawings, health permits, a liquor license application, and legal review totaling 22000.",
            "general": "Permit fees, an attorney's review of the lease, and insurance during the build, totaling 15000.",
        },
    },
    "preopening_working_capital": {
        "what": "Cash you need to hold before opening day: first inventory, payroll while you train staff, rent before sales start, and a small cash cushion.",
        "why": "Businesses spend before they earn. This line shows how much cash must be on hand to survive until sales cover costs.",
        "how": "Estimate the weeks between signing the lease and the first sale. Add rent, payroll, utilities, and first inventory for those weeks.",
        "avoid": "Entering your whole savings. Counting costs already listed under Soft costs or Construction cost.",
        "method": "Method: weeks before opening × weekly costs, plus first inventory. If you leave it blank RUGD uses 0 for this line.",
        "example": {
            "hospitality": "Eight weeks of rent and payroll while building and training, plus opening food and paper goods, 40000 in total.",
            "general": "Six weeks of rent and wages before your first customer, plus starting inventory, 30000 in total.",
        },
    },
    "contingency_pct": {
        "what": "A cushion, as a share of the other one-time costs, for surprises such as a quote that comes in high.",
        "why": "Projects rarely cost exactly what was quoted. A cushion keeps the plan from breaking at the first surprise.",
        "how": "Use a share you can defend, based on how firm your quotes are. Enter it as a decimal: 0.10 means 10 percent. Firm written quotes may justify a smaller cushion than rough estimates.",
        "avoid": "Entering 10 when you mean 10 percent. The field expects 0.10.",
        "method": "Method: the cushion is applied to construction, equipment, soft costs, and pre-opening working capital. If you leave it blank RUGD uses its coded placeholder of 0.10. That placeholder is not an industry standard.",
        "example": {
            "general": "With 300000 of other costs, a 0.10 cushion adds 30000. A 0.15 cushion adds 45000. Illustration only.",
        },
    },
    "debt_share": {
        "what": "The share of the opening cost that you plan to pay for with a loan rather than your own money.",
        "why": "Borrowing creates a yearly loan payment that the business must cover, so it changes the cash-flow and break-even views.",
        "how": "Ask a lender what share they would finance for a business like yours. Enter it as a decimal: 0.40 means 40 percent borrowed.",
        "avoid": "Leaving it blank without knowing that RUGD then uses its placeholder of 0.70, which assumes most of the cost is borrowed. That placeholder is not advice or a lender's term.",
        "method": "Method: debt = total opening cost × this share. The rest is your equity.",
        "example": {
            "general": "With a total opening cost of 400000 and a share of 0.40, debt is 160000 and your own money is 240000. Illustration only.",
        },
    },
    "annual_interest_rate": {
        "what": "The yearly interest rate on the loan, as a decimal.",
        "why": "It sets the size of the loan payment. A higher rate means a higher yearly payment.",
        "how": "Use a rate from a lender's quote or term sheet. Enter 0.08 for 8 percent.",
        "avoid": "Entering 8 instead of 0.08. Using a teaser rate that resets.",
        "method": "Method: standard loan payment from the debt, rate, and years. If you leave it blank RUGD uses its placeholder of 0.08, which is not a market rate.",
        "example": {
            "general": "A lender quotes 7.5 percent. Enter 0.075. Illustration only.",
        },
    },
    "amortization_years": {
        "what": "The number of years over which the loan is paid off.",
        "why": "A longer period lowers each yearly payment but costs more interest over time.",
        "how": "Use the term in the lender's quote. Enter a whole number of years.",
        "avoid": "Entering months instead of years.",
        "method": "Method: the loan payment is spread evenly over this many years. If you leave it blank RUGD uses its placeholder of 20 years. That placeholder is not a lender's term or an industry standard.",
        "example": {
            "general": "A 10-year term is entered as 10. Illustration only.",
        },
    },
    "annual_fixed_costs": {
        "what": "Yearly costs you pay whether or not you sell much: rent, insurance, salaried pay, software, and basic utilities.",
        "why": "Contribution from sales has to cover these costs before the business keeps any profit. They also set the break-even revenue.",
        "how": "Add up the monthly amounts for each fixed cost and multiply by 12. Use quotes or contracts where you can, such as the lease.",
        "avoid": "Counting food, packaging, hourly labor, or card fees here if they are already in the margin. Counting loan payments here, because RUGD adds the loan payment separately.",
        "method": "Method: yearly total of fixed costs. If you leave it blank RUGD uses 0 for this line, which makes the result look better than it may be.",
        "example": {
            "hospitality": "Rent 6000 a month, insurance 500, base utilities 800, and a salaried manager at 4500 is 11800 a month, or 141600 a year.",
            "general": "Rent 3000 a month, insurance 300, software 200, and a salaried owner draw of 3500 is 7000 a month, or 84000 a year.",
        },
    },
    "downside_multiplier": {
        "what": "A stress test. It scales your occupancy down to show what a weaker year looks like.",
        "why": "It lets you see whether the plan still works if sales are lower than hoped.",
        "how": "Choose a fraction of your base occupancy that you would consider a bad but realistic year. 0.70 means occupancy is 70 percent of your base.",
        "avoid": "Treating it as an industry standard. It is your own assumption. A value above 1 is not a downside.",
        "method": "Method: weekday and weekend occupancy are each multiplied by this number. If you leave it blank RUGD uses its placeholder of 0.6. That placeholder is not an industry standard.",
        "example": {
            "general": "With a base weekday occupancy of 0.50 and a multiplier of 0.70, the downside uses 0.35. Illustration only.",
        },
    },
    "seats": {
        "what": "How many customers you can serve at one time. For a restaurant, this is the number of seats.",
        "why": "It is the cap on how much you can sell. Seats times how full they are times the average ticket is the model's yearly revenue line.",
        "how": "Count seats from your floor plan, including bar and patio seats you will really use. Use a layout that fits your fire and health code limits.",
        "avoid": "Counting standing room or seats you will not staff. Using seats as a stand-in for table turns, which the model does not have. See the turnover note below.",
        "method": "Method: one cover per occupied seat per operating day. There is no turnover or multiple-seating input. Occupancy cannot exceed 1, so the model cannot show more covers in a day than you have seats. If your plan turns tables several times a day, the model will understate revenue. That is a known limit of this version. A change is proposed for RUGD review and has not been made.",
        "example": {
            "hospitality": "A 30-seat cafe with 20 seats inside and 10 on a patio you will staff in season.",
            "retail": "The startup formula counts seated capacity. If your shop has no seats, you can leave the startup build blank and use the revenue worksheet and the monthly figures, or enter the closest capacity you can defend and say so in your notes. The model will treat it as one customer per unit per day.",
            "software": "The startup formula counts seated capacity. A software business usually has no seats. Leave the startup build blank and use the revenue worksheet and the monthly figures, unless you can defend a capacity unit and note it.",
            "healthcare": "Treatment chairs or exam rooms you will staff. The model treats each as one patient per day.",
            "services": "Workstations or consulting rooms you will staff. The model treats each as one client per day.",
            "general": "Use the capacity unit that limits your sales, and say in your notes what you counted. The model treats each unit as one customer per day.",
        },
    },
    "average_ticket": {
        "what": "The average amount one customer spends in one visit, before tax and tips. For a restaurant, the average check per cover.",
        "why": "It converts customers into revenue. A small change moves revenue across every seat and every day.",
        "how": "Add up what a typical visit buys: a drink, a main, a side. If you are open, divide sales by covers. If you are new, list two or three typical orders and average them against nearby menus.",
        "avoid": "Including tax or tips. Including a second seating or a second visit in one ticket, because the model already counts one cover per occupied seat per day. Using the top dish price instead of the average.",
        "method": "Method: revenue per customer per visit.",
        "example": {
            "hospitality": "Lunch averages 14 and dinner averages 26 per cover. If lunch and dinner are about equally common, the all-day average is about 20. Illustration only.",
            "retail": "If the typical basket is one 28 item and one 12 item, the average sale is 40. Illustration only.",
            "software": "For software, the monthly price is usually the better figure. Use the revenue worksheet.",
            "healthcare": "The average fee per visit. Use the revenue worksheet for visits and fee.",
            "services": "The average fee per client visit or job. Use the revenue worksheet for billable time or retainers.",
            "general": "Total sales divided by the number of customers, or the average of a few typical orders. Illustration only.",
        },
    },
    "weekday_occupancy": {
        "what": "The share of your seats that are filled on an average Monday to Friday, as a decimal from 0 to 1.",
        "why": "It drives the largest part of weekly sales. The model counts weekdays as 5 of every 7 operating days.",
        "how": "Estimate covers served on a typical weekday and divide by seats. If you serve 15 customers a day on 30 seats, enter 0.50. Use traffic counts from a similar location, a landlord's data, or your own trial days if you have them.",
        "avoid": "Entering 50 instead of 0.50. Entering your best day instead of an average. Entering more than 1: the model refuses it.",
        "method": "Method: weekday occupancy is applied to 5/7 of operating days. Those weights are calendar shares, not market figures, and they apply whichever days you are open.",
        "example": {
            "hospitality": "Your lunch rush fills 24 of 30 seats for two hours, but the cafe is quiet the rest of the day. Over the whole day about 12 seats are in use, so enter 0.40. Illustration only.",
            "general": "If you serve 12 customers on an average weekday and you can serve 24 at once, enter 0.50. Illustration only.",
        },
    },
    "weekend_occupancy": {
        "what": "The share of your seats that are filled on an average Saturday or Sunday, as a decimal from 0 to 1.",
        "why": "Weekends are often busier or quieter than weekdays. The model counts weekends as 2 of every 7 operating days.",
        "how": "Estimate covers on a typical weekend day and divide by seats. Compare with nearby places on a weekend, and use your trial days if you have them.",
        "avoid": "Entering 70 instead of 0.70. Assuming weekends are always busier. Entering a figure for a day you will be closed.",
        "method": "Method: weekend occupancy is applied to 2/7 of operating days, whichever days you are open. If you are closed on weekends, the model still weights them. Enter an occupancy that reflects the weighted average you expect.",
        "example": {
            "general": "A cafe near an office park is quieter on weekends. 8 customers on a typical weekend day with 30 seats gives 0.27. Illustration only.",
        },
    },
    "operating_days": {
        "what": "How many days a year you expect to be open and selling.",
        "why": "Revenue in the seat formula is seats × occupancy × average ticket × this number. It is a yearly figure, so it scales the whole first-year revenue line.",
        "how": "Pick the weekdays you will be open and the weeks you will be open in the schedule helper below this field. It shows days a year and days a month, and fills this box only when you choose Use. Subtract holidays and planned closures if you want them counted.",
        "avoid": "Entering days a month here. Counting days you plan to be closed. Assuming the schedule changes the weekday and weekend weights: the model always uses 5/7 weekdays and 2/7 weekend days.",
        "method": "Method: operating days per year, up to 366. The seat formula uses it as the number of days in the year being estimated.",
        "example": {
            "hospitality": "Open 6 days a week for 50 weeks is 300 operating days a year, or 25 a month. Illustration only.",
            "general": "Open 5 days a week for 52 weeks is 260 operating days a year, about 21.7 a month. Illustration only.",
        },
    },
    "contribution_margin": {
        "what": "The share of each sales dollar left after the costs that rise and fall with sales: ingredients or goods, packaging, card fees, and hourly labor.",
        "why": "It is what pays for rent, loans, and profit. A small error here changes break-even and cash flow a lot.",
        "how": "Add the variable cost of a typical sale, divide by the average ticket, and subtract from 1. Enter it as a decimal: 0.60 means 60 percent is left after variable costs. If your costs are quoted per item, use real supplier prices.",
        "avoid": "Entering 60 instead of 0.60. Counting rent or salaried pay here, because they belong in Annual fixed costs. Counting food cost twice. Confusing it with profit margin, which is lower.",
        "method": "Method: (sales minus variable costs) divided by sales. This is your own estimate unless you have measured it. The startup view is revenue × margin minus annual fixed costs.",
        "example": {
            "hospitality": "A 20 check where food and paper cost 6, card fees 0.60, and hourly labor 5.40 leaves 8, which is 0.40. Illustration only.",
            "retail": "A 40 sale where the goods cost 22 and card fees are 1.20 leaves 16.80, which is 0.42. Illustration only.",
            "software": "A 100 monthly subscription where hosting and support cost 18 leaves 82, which is 0.82. Illustration only.",
            "healthcare": "A 150 visit where supplies and hourly assistants cost 60 leaves 90, which is 0.60. Illustration only.",
            "services": "A 100 billable hour where subcontractor and direct costs are 35 leaves 65, which is 0.65. Illustration only.",
            "general": "Sales of 100 with 55 of variable costs leaves 45, which is 0.45. Illustration only.",
        },
    },
    "initial_capital": {
        "what": "The cash you have set aside for the business at the start.",
        "why": "The analysis compares it with monthly cash flow to show how long that cash could last or how long it would take to recover.",
        "how": "Use cash you can actually commit, not credit limits or money you hope to raise. Statements or a signed commitment make it more reliable.",
        "avoid": "Counting borrowed money that is not approved. Counting the same money as your opening costs and again here without noting it.",
        "method": "Method: your own figure for starting cash. It is an assumption unless a record verifies it.",
        "example": {
            "general": "70000 of savings you will put in, held in a business account. Illustration only.",
        },
    },
    "monthly_fixed_costs": {
        "what": "Costs you pay every month no matter how much you sell: rent, insurance, salaried pay, software, and base utilities.",
        "why": "The monthly view subtracts them from what is left of sales. They also set the monthly break-even revenue.",
        "how": "Add up your recurring bills for a normal month. Use the lease and contracts for rent and insurance.",
        "avoid": "Counting ingredients or goods here if they are in your margin. Counting loan payments unless you are doing so on purpose.",
        "method": "Method: monthly cash flow = projected monthly revenue × gross margin − monthly fixed costs.",
        "example": {
            "hospitality": "Rent 6000, insurance 500, base utilities 800, and a salaried manager at 4500 total 11800 a month. Illustration only.",
            "general": "Rent 2500, insurance 250, software 250, and phone 100 total 3100 a month. Illustration only.",
        },
    },
    "gross_margin_pct": {
        "what": "The share of each sales dollar left after the direct cost of what you sold, as a decimal.",
        "why": "The monthly view multiplies revenue by it, so it controls how much of each sale can pay for fixed costs.",
        "how": "Subtract the direct cost of a typical sale from its price and divide by the price. Enter 0.55 for 55 percent. If you used a contribution margin above, keep the two figures consistent.",
        "avoid": "Entering 55 instead of 0.55. Counting fixed costs in the cost of sales.",
        "method": "Method: (price minus direct cost) divided by price. Zero margin cannot define a break-even and is flagged.",
        "example": {
            "hospitality": "A 20 check with 9 of food, drink, and paper cost leaves 11, or 0.55. Illustration only.",
            "software": "A 100 monthly price with 20 of hosting and support leaves 80, or 0.80. Illustration only.",
            "general": "A 50 sale with 22 of goods cost leaves 28, or 0.56. Illustration only.",
        },
    },
    "projected_monthly_revenue_base": {
        "what": "How much you expect to sell in a typical month, before costs.",
        "why": "It is the starting point of the monthly view: revenue times gross margin, minus fixed costs, gives cash flow.",
        "how": "Use the method in the revenue step: customers times price for your industry, or an independent estimate you can support. A trial month, a pre-order list, or a quote from a similar location is stronger than a guess.",
        "avoid": "Copying an annual figure into a monthly field. Using your best month. Counting tax or tips.",
        "method": "Method: your own monthly figure. The revenue method on this page can suggest one from your assumptions. Copying it never saves or runs an analysis for you.",
        "example": {
            "hospitality": "If the yearly seat formula gives 108000 over 300 operating days, a typical month is about 9000. Divide a yearly figure by 12 only if you are open all year. Illustration only.",
            "general": "40 customers a week at 25 each is about 4300 a month (40 × 25 × 52 ÷ 12). Illustration only.",
        },
    },
    "forecast_people": {
        "what": "How many people will bill clients' time.",
        "why": "Billable time is limited by how many people can sell it.",
        "how": "Count people who do client work, not owners who mostly manage. Use full-time equivalents if some are part time.",
        "avoid": "Counting support staff who do not bill.",
        "example": {"general": "Two consultants who bill. Illustration only."},
    },
    "forecast_hours": {
        "what": "The billable hours each person will sell in a month, not the hours they work.",
        "why": "Not every hour is billable. Selling, admin, and training take time.",
        "how": "Start from the hours a person works in a month and subtract time you will not bill. Use your own timesheets if you have them.",
        "avoid": "Assuming every working hour is billable.",
        "example": {"general": "A person who works about 160 hours a month and bills 100 of them. Illustration only."},
    },
    "forecast_rate": {
        "what": "The price per hour you charge a client.",
        "why": "Rate times billable hours times people is the revenue line for this method.",
        "how": "Use what clients will really pay. Ask for quotes from similar firms in your market or look at your own past invoices.",
        "avoid": "Using the list rate if you often discount.",
        "example": {"general": "A rate of 120 an hour. Illustration only."},
    },
    "forecast_clients": {
        "what": "How many clients will pay you a regular fee each month.",
        "why": "Retainers give steadier revenue than one-off jobs, so the number of clients drives the revenue line.",
        "how": "Count clients who have said yes or signed, then add those you can reasonably expect to sign. Keep them separate in your notes.",
        "avoid": "Counting prospects as clients.",
        "example": {"general": "Eight clients on a monthly retainer. Illustration only."},
    },
    "forecast_fee": {
        "what": "The fee for one unit: the monthly fee per retainer client, or the fee for one patient visit.",
        "why": "Fee times the number of clients or visits is the revenue line for this method.",
        "how": "Use the price clients or patients really pay, not the list price. For visits, use what you collect after discounts. It is not a payer rate.",
        "avoid": "Entering the list price when you expect discounts or write-offs.",
        "example": {
            "services": "A monthly retainer of 1500 per client. Illustration only.",
            "healthcare": "A fee collected per visit of 140. Illustration only.",
            "general": "A monthly fee of 1500 per client. Illustration only.",
        },
    },
    "forecast_transactions": {
        "what": "How many sales you expect in a month.",
        "why": "Transactions times the average sale is the revenue line for a shop.",
        "how": "Estimate customers per day times days open. Use foot traffic counts, trial days, or a comparable shop.",
        "avoid": "Counting browsers as buyers.",
        "example": {"general": "30 sales a day over 26 open days is 780 a month. Illustration only."},
    },
    "forecast_average_sale": {
        "what": "The average amount of one sale.",
        "why": "It converts transactions into revenue.",
        "how": "Add up what a typical basket buys. If you are open, divide sales by transactions.",
        "avoid": "Including tax. Using your biggest sale.",
        "example": {"general": "An average basket of 40. Illustration only."},
    },
    "forecast_customers": {
        "what": "How many customers will pay you each month.",
        "why": "Paying customers times the monthly price is the revenue line for a subscription.",
        "how": "Count paying customers, not free trials. Think about how many you can win each month and how many will cancel.",
        "avoid": "Counting trial users as paying.",
        "example": {"general": "120 paying customers by month 12. Illustration only."},
    },
    "forecast_monthly_price": {
        "what": "What one customer pays each month.",
        "why": "It converts paying customers into monthly revenue.",
        "how": "Use the plan price after discounts. Use an average if you have several plans.",
        "avoid": "Using an annual price as a monthly one.",
        "example": {"general": "A monthly price of 49. Illustration only."},
    },
    "forecast_visits": {
        "what": "How many patient visits you expect in a month.",
        "why": "Visits times the fee per visit is the revenue line for a clinic.",
        "how": "Estimate visits per provider per day times days open. Check against your scheduling capacity.",
        "avoid": "Counting visits you cannot schedule.",
        "example": {"general": "A provider seeing 14 patients a day over 20 days is 280 a month. Illustration only."},
    },
    "verified_revenue_trailing_12m": {
        "what": "Revenue the business actually collected in the last 12 months, taken from a record you can show.",
        "why": "It is the only revenue figure here that can count as verified evidence, and only together with a verified source and a written reason.",
        "how": "Use tax returns, bank statements, or point-of-sale reports. Leave it blank for a business that has not started selling.",
        "avoid": "Entering a forecast here. A customer entry, a note, or a hypothetical demonstration is not verified evidence and does not clear a demand flag.",
        "method": "Method: your records, stated for the last 12 months. It is applied only when the source is marked verified and a rationale is present.",
        "example": {"general": "The total sales line from your last 12 months of bank deposits, with the statements saved. Illustration only."},
    },
    "inputs_are_measured": {
        "what": "A check box that says the monthly figures come from real records instead of estimates.",
        "why": "It tells the analysis how much weight your figures carry. Estimates stay labeled as assumptions.",
        "how": "Check it only if all four monthly figures come from statements or reports. Leave it unchecked if any figure is a guess.",
        "avoid": "Checking it for a plan that has not started. Checking it does not make the figures verified evidence.",
        "method": "Method: this is your statement. It is not the verified demand record.",
        "example": {"general": "A business that has run for a year can check it if its monthly figures come from its books."},
    },
    "service_style": {
        "what": "Whether guests are served at the table or order at a counter.",
        "why": "The stored restaurant medians are split by this choice, so it decides which ones can be shown to you.",
        "how": "Pick the one that describes most of your sales. Leave it blank if you are unsure. Nothing else depends on it.",
        "avoid": "Choosing the style of a place you admire instead of the one you will run.",
        "method": "Method: used only to filter the benchmark list. It changes no number in your draft.",
        "example": {"general": "A table-service dining room is full service. A counter order with food brought out is limited service."},
    },
    "venue_sqft": {
        "what": "The total floor area of the space you will lease or build, in square feet.",
        "why": "With a source you record, it lets RUGD cross-check your seat count and construction cost. It is optional.",
        "how": "Take it from the lease, the listing, or the floor plan. Say in your notes whether it includes kitchen and storage.",
        "avoid": "Using only the dining room area and then comparing it with a rate that covers the whole building.",
        "method": "Method: seats and construction cost are only cross-checked against figures you record. Nothing is estimated from it.",
        "example": {"general": "A 2,400 square foot lease with a 1,300 square foot dining room. Illustration only."},
    },
    "construction_scope": {
        "what": "What kind of building work the construction cost covers.",
        "why": "Rates and risks differ a lot between a new building, an empty shell, and a renovation, so a cost without a scope is hard to judge.",
        "how": "Pick the closest description. It is a label for your own reference and for suggestions.",
        "avoid": "Comparing a shell build-out cost with a figure for a finished space.",
        "method": "Method: label only. It changes no number.",
        "example": {"general": "Gutting an empty retail shell to add a kitchen is a build-out of an empty shell."},
    },
    "available_cash": {
        "what": "The cash you could put into the project yourself and can show on a statement.",
        "why": "It is the other half of financing. RUGD uses it to show the funding gap and to size the debt share you test.",
        "how": "Use cash on hand or documented commitments. Do not count money you may raise later.",
        "avoid": "Counting your whole savings, or money a lender will want to see as untouched reserves.",
        "method": "Method: compared with total project cost. It does not set your debt share unless you choose it in a scenario or accept a suggestion.",
        "example": {"general": "A bank balance of 150000 set aside for the project. Illustration only."},
    },
    "staff_fte": {
        "what": "How many full-time-equivalent people you plan to employ at a normal week, counting two half-time people as one.",
        "why": "Payroll is usually the largest running cost. Staffing next to your fixed costs helps you catch a payroll that is missing from your numbers.",
        "how": "Add the weekly hours of everyone on the schedule and divide by 40.",
        "avoid": "Counting owners who will not draw pay, or forgetting that a restaurant needs staff for every open hour.",
        "method": "Method: compared with fixed costs as a consistency check. It changes no number.",
        "example": {"general": "Ten people averaging 28 hours a week is seven full-time equivalents. Illustration only."},
    },
    "avg_hourly_wage": {
        "what": "The average hourly pay you expect to give your staff, including any employer taxes and benefits you want counted.",
        "why": "With staffing, it shows what payroll could cost over a year.",
        "how": "Use wage data for your area and role from a public wage survey, or offers you have made. The Benchmarks page lists where to look.",
        "avoid": "Using the minimum wage when tips, tenure, or local competition will push pay higher.",
        "method": "Method: staff × wage × 2,080 hours is shown as a check. It changes no number.",
        "example": {"general": "An all-in average of 19 an hour. Illustration only."},
    },
}

_SECTION_INTROS = {
    "opening": (
        "What it costs to open",
        "Start with the one-time money you need before your first sale. These answers set how much you must raise or borrow, and they feed the loan and cash-flow views.",
    ),
    "sales": (
        "How much you could sell",
        "This section estimates a year of sales from how many customers you can serve, how full you expect to be, and what each customer pays. The profit and break-even views start from this line.",
    ),
    "margin": (
        "What you keep from each sale",
        "Not every sales dollar is profit. This answer captures the share left after the costs that rise and fall with sales, so the analysis can compare it with your fixed costs and loan payments.",
    ),
    "worksheet": (
        "Financing and yearly costs",
        "These optional lines refine the startup picture: other one-time costs, how much you borrow, and the costs you pay every year regardless of sales. A blank line is not zero. Where RUGD fills in a placeholder number, the help for that field says so.",
    ),
    "monthly": (
        "Monthly figures",
        "These four figures drive the monthly cash-flow and break-even view: starting cash, fixed costs, how much of each sale you keep, and typical monthly sales. They are your assumptions until a record verifies them.",
    ),
    "forecast": (
        "How revenue is estimated",
        "Pick the way of estimating revenue that fits your kind of business. It shows the arithmetic from your own numbers. It does not replace the official result.",
    ),
}

_FAMILY_OPENING = {
    "hospitality": "For a restaurant or cafe, the startup path works from seats, how full they are, the average check, and the days you open.",
    "retail": "For a shop, you can use the startup path if you can defend a capacity unit. Otherwise the revenue worksheet and the monthly figures carry the estimate.",
    "software": "A software business has little to build. If there is no physical setup, use the revenue worksheet and the monthly figures instead of the startup path.",
    "healthcare": "For a clinic, treat chairs or exam rooms as capacity. The revenue worksheet for visits and fee is often the closer fit.",
    "services": "For a services firm, the revenue worksheet for billable time or retainers is usually the closer fit. The startup path counts seated capacity.",
}


def has_help(key: str) -> bool:
    return key in _HELP


def help_keys() -> tuple[str, ...]:
    return tuple(_HELP)


def _example(entry: dict[str, Any], family: str) -> str:
    examples = entry.get("example") or {}
    return str(examples.get(family) or examples.get("general") or "")


def _num(profile: dict[str, Any], key: str) -> float | None:
    if field_state(profile.get(key)) not in {"entered", "zero"}:
        return None
    try:
        return float(str(profile.get(key)).strip())
    except ValueError:
        return None


def _money(value: float) -> str:
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


def _revenue(profile: dict[str, Any], **override: float) -> float | None:
    """The existing seat formula on the customer's own entries. Nothing is stored."""
    values = {
        "seats": _num(profile, "seats"),
        "average_ticket": _num(profile, "average_ticket"),
        "weekday_occupancy": _num(profile, "weekday_occupancy"),
        "weekend_occupancy": _num(profile, "weekend_occupancy"),
        "operating_days": _num(profile, "operating_days"),
    }
    values.update(override)
    if any(value is None for value in values.values()):
        return None
    try:
        return seat_occupancy_revenue(
            values["seats"],  # type: ignore[arg-type]
            values["average_ticket"],  # type: ignore[arg-type]
            values["weekday_occupancy"],  # type: ignore[arg-type]
            values["weekend_occupancy"],  # type: ignore[arg-type]
            values["operating_days"],  # type: ignore[arg-type]
        ).revenue
    except ValueError:
        return None


def _yours(key: str, profile: dict[str, Any], family: str) -> str:
    """One sentence built from the customer's own answers. Empty when there is nothing to say."""
    industry = " ".join(str(profile.get("industry") or "").split())
    market = " ".join(str(profile.get("market") or "").split())
    model = " ".join(str(profile.get("revenue_model") or "").split())
    place = f" in {market}" if market else ""
    if key in {"construction_cost", "equipment", "soft_costs"} and market:
        return f"You said your market is {market}. Ask for quotes and fee schedules from firms and offices there."
    if key == "seats" and industry:
        return f"You described the business as {industry}{place}. Count the capacity that limits your sales."
    if key == "average_ticket":
        base = _revenue(profile, average_ticket=1.0)
        if base is not None:
            return (
                f"With the other figures you entered, each 1 of average ticket moves the seat formula's yearly revenue by about {_money(base)}. "
                "That is arithmetic on your entries, not a forecast."
            )
    if key == "weekday_occupancy":
        current = _num(profile, "weekday_occupancy")
        ticket = _num(profile, "average_ticket")
        if current is not None and ticket is not None and current + 0.1 <= 1:
            low = _revenue(profile)
            high = _revenue(profile, weekday_occupancy=current + 0.1)
            if low is not None and high is not None:
                return (
                    f"With your other entries, 0.10 more weekday occupancy adds about {_money(high - low)} a year. "
                    "That is arithmetic on your entries, not a forecast."
                )
    if key == "operating_days":
        schedule = parse_schedule(str(profile.get("operating_schedule") or ""))
        weeks = _weeks(profile.get("operating_weeks"))
        if schedule and weeks is not None:
            estimate = operating_estimate(schedule, weeks)
            return (
                f"Your saved weekly schedule gives {estimate['annual_days']} operating days a year. "
                "Your saved operating days stay as they are until you choose Use."
            )
    if key == "contribution_margin":
        revenue = _revenue(profile)
        margin = _num(profile, "contribution_margin")
        if revenue is not None and margin is not None and 0 <= margin <= 1:
            return (
                f"At the yearly revenue your entries give ({_money(revenue)}), a margin of {margin:g} leaves about "
                f"{_money(revenue * margin)} before fixed costs. That is arithmetic on your entries, not a forecast."
            )
    if key == "projected_monthly_revenue_base" and model:
        return f"You described the revenue model as: {model[:160]}. Make the monthly figure match that description."
    if key in {"monthly_fixed_costs", "annual_fixed_costs"} and market:
        return f"Use real quotes for rent, insurance, and utilities in {market}."
    return ""


def label_with_help(key: str, label: str, profile: dict[str, Any], *, for_id: str = "", suffix: str = "") -> str:
    """Label plus a help disclosure. Opening help does not interrupt entry or change a value."""
    target = escape(for_id or key)
    base = f'<label for="{target}">{escape(label)}</label>'
    if key not in _HELP:
        return base
    return f'<div class="field-label">{base}{help_html(key, label, profile, suffix)}</div>'


def help_html(key: str, label: str, profile: dict[str, Any], suffix: str = "") -> str:
    entry = _HELP[key]
    family = family_for(str(profile.get("industry") or ""))
    example = _example(entry, family)
    yours = _yours(key, profile, family)
    benchmark = str(entry.get("bench") or BENCHMARK_DEFAULT)
    method = str(entry.get("method") or "")
    bits = [
        f'<p><strong>What it means.</strong> {escape(entry["what"])}</p>',
        f'<p><strong>Why it matters.</strong> {escape(entry["why"])}</p>',
    ]
    if example:
        if "illustration" not in example.lower():
            example = f"{example} Illustration only."
        bits.append(f'<p><strong>Example.</strong> {escape(example)}</p>')
    if yours:
        bits.append(f'<p class="help-yours"><strong>From your answers.</strong> {escape(yours)}</p>')
    more = [f'<p><strong>How to estimate it.</strong> {escape(entry["how"])}</p>']
    more.append(f'<p><strong>Common mistakes.</strong> {escape(entry["avoid"])}</p>')
    if method:
        more.append(f'<p class="help-method">{escape(method)}</p>')
    more.append(f'<p><strong>Benchmarks.</strong> {escape(benchmark)}</p>')
    field = escape(key)
    return (
        f'<details class="help" id="help-{field}{escape(suffix)}" data-help="{field}">'
        f'<summary aria-label="Help: {escape(label)}"><span aria-hidden="true">?</span></summary>'
        f'<div class="help-body" role="note">{"".join(bits)}'
        '<details class="help-more"><summary>How to estimate it, mistakes to avoid, and benchmarks</summary>'
        f'{"".join(more)}</details></div></details>'
    )


def checkbox_help(key: str, label: str, profile: dict[str, Any]) -> str:
    return help_html(key, label, profile) if key in _HELP else ""


_FAMILY_SECTION = {
    "sales": {
        "hospitality": "For a restaurant: seats you can serve, how full they are on weekdays and weekends, the average check per guest, and the days you open. The model counts one cover per occupied seat per day, so it has no table-turn input.",
        "retail": "For a shop, use a capacity you can defend, such as customers served at once, with the average sale and the days you open.",
        "software": "A software business usually forecasts from paying customers and price. The revenue worksheet is the closer fit.",
        "healthcare": "For a clinic, think in visits per day and fee per visit. Chairs or rooms set the capacity.",
        "services": "For a services firm, think in billable hours or retainers. The revenue worksheet is the closer fit.",
    },
    "margin": {
        "hospitality": "For a restaurant, costs that move with sales include food and paper, card fees, and hourly labor.",
        "retail": "For a shop, costs that move with sales include the cost of goods, card fees, and sales commissions.",
        "software": "For software, costs that move with sales include hosting per customer, support, and payment fees.",
        "healthcare": "For a clinic, costs that move with visits include supplies, lab fees, and hourly clinical staff.",
        "services": "For a services firm, costs that move with work sold include contractors and direct labor.",
    },
}


def section_intro(section: str, profile: dict[str, Any]) -> str:
    title, text = _SECTION_INTROS[section]
    family = family_for(str(profile.get("industry") or ""))
    extra = ""
    if section == "opening":
        extra = _FAMILY_OPENING.get(family, "")
    elif section in _FAMILY_SECTION:
        extra = _FAMILY_SECTION[section].get(family, "")
    market = " ".join(str(profile.get("market") or "").split())
    if section == "opening" and market:
        extra = (extra + " " if extra else "") + f"Ask for quotes from firms in {market}."
    tail = f' <span class="muted">{escape(extra)}</span>' if extra else ""
    return (
        f'<div class="section-intro" data-section="{escape(section)}"><h4>{escape(title)}</h4>'
        f"<p>{escape(text)}{tail}</p></div>"
    )


def parse_schedule(raw: str) -> list[str]:
    allowed = {code for code, _label in DAYS}
    chosen = []
    for part in str(raw or "").split(","):
        code = part.strip().lower()
        if code in allowed and code not in chosen:
            chosen.append(code)
    return [code for code, _label in DAYS if code in chosen]


def _weeks(raw: Any) -> float | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value != value or value <= 0 or value > 52:
        return None
    return value


def operating_estimate(days: list[str], weeks: float | None) -> dict[str, Any]:
    """Transparent arithmetic. A blank week count is shown as 52 and labeled as assumed."""
    assumed = weeks is None
    used = 52.0 if weeks is None else weeks
    count = len(days)
    annual = int(count * used + 0.5)
    monthly = int(count * used / 12 * 10 + 0.5) / 10
    weekend = len([day for day in days if day in _WEEKEND])
    share = (weekend / count) if count else None
    return {
        "days_per_week": count,
        "weeks": used,
        "weeks_assumed": assumed,
        "annual_days": annual,
        "monthly_days": monthly,
        "weekend_share": share,
    }


def _number_text(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def estimate_text(profile: dict[str, Any]) -> str:
    days = parse_schedule(str(profile.get("operating_schedule") or ""))
    raw_weeks = profile.get("operating_weeks")
    weeks = _weeks(raw_weeks)
    if str(raw_weeks or "").strip() and weeks is None:
        return "Enter weeks open per year between 1 and 52."
    if not days:
        return "Pick the days you plan to be open to see an estimate."
    est = operating_estimate(days, weeks)
    note = " The week count of 52 is assumed. Enter fewer if you will close for weeks." if est["weeks_assumed"] else ""
    text = (
        f"Open {est['days_per_week']} days a week × {_number_text(est['weeks'])} weeks = {est['annual_days']} operating days a year. "
        f"That is about {_number_text(est['monthly_days'])} operating days a month ({est['annual_days']} ÷ 12).{note}"
    )
    share = est["weekend_share"]
    if share is not None and abs(share - ASSUMED_WEEKEND_SHARE) > 0.005:
        text += (
            f" Weekend days are {int(share * 100 + 0.5)}% of the days you picked. The model always treats 5/7 of operating days "
            f"as weekdays and 2/7 as weekend days, about {int(ASSUMED_WEEKEND_SHARE * 100 + 0.5)}% weekend, whichever days you open. "
            "Enter weekday and weekend occupancy as averages that fit that weighting."
        )
    saved = _num(profile, "operating_days")
    if saved is not None:
        if int(saved) == est["annual_days"] and float(saved).is_integer():
            text += f" This matches your operating days entry ({_number_text(saved)})."
        else:
            text += f" Your operating days entry is {_number_text(saved)}. It stays as it is until you choose Use."
    return text


def schedule_html(profile: dict[str, Any], locked: str) -> str:
    """Seven-day selector. It suggests a number. The operating_days field changes only on Use."""
    days = parse_schedule(str(profile.get("operating_schedule") or ""))
    raw_weeks = str(profile.get("operating_weeks") or "")
    weeks = _weeks(raw_weeks)
    boxes = "".join(
        f'<label class="day"><input type="checkbox" data-day="{code}" value="{code}"'
        f'{" checked" if code in days else ""} {locked}><span>{label}</span></label>'
        for code, label in DAYS
    )
    estimate = operating_estimate(days, weeks) if days and not (raw_weeks.strip() and weeks is None) else None
    use_value = estimate["annual_days"] if estimate else ""
    use_hidden = "" if estimate else " hidden"
    use_button = (
        ""
        if locked
        else (
            f'<button type="button" id="schedule-use" data-value="{use_value}"{use_hidden}>'
            f'Use {escape(str(use_value))} as operating days</button>'
        )
    )
    return f"""
<section class="schedule" id="operating-schedule" data-assumed-weekend="{ASSUMED_WEEKEND_SHARE:.6f}">
<h4>Plan operating days from a weekly schedule</h4>
<p class="muted">Pick the days you plan to be open. This suggests a number. The operating days field does not change until you choose Use.</p>
<fieldset class="days" aria-label="Days open each week">{boxes}</fieldset>
<input type="hidden" name="operating_schedule" value="{escape(','.join(days))}">
<label for="operating_weeks">Weeks open per year</label>
<input id="operating_weeks" name="operating_weeks" value="{escape(raw_weeks)}" inputmode="numeric" placeholder="52" {locked}>
<p class="schedule-estimate" id="schedule-estimate" aria-live="polite">{escape(estimate_text(profile))}</p>
{use_button}
</section>
"""
