"""JavaScript run inside the LinkedIn page. Kept here so selectors live in one place.

LinkedIn's jobs UI uses hashed CSS classes, so we only rely on stable hooks such as
`componentkey="job-card-component-ref-<id>"`. Cards are never clicked: opening a job on LinkedIn
marks it as "Viewed", which would corrupt the status we want to show.
"""

CARD_SELECTOR = 'div[componentkey^="job-card-component-ref-"]'

EXTRACT_CARDS = """
() => [...document.querySelectorAll('div[componentkey^="job-card-component-ref-"]')]
  .filter(el => !el.parentElement.closest('[componentkey^="job-card-component-ref-"]'))
  .map(el => ({
    id: el.getAttribute('componentkey').replace('job-card-component-ref-', ''),
    ps: [...el.querySelectorAll('p')].map(p => p.innerText.trim()),
    hidden_title: el.querySelector('p span[aria-hidden="true"]')?.innerText.trim() || '',
  }))
"""

EXTRACT_SEARCH_LINKS = """
() => [...document.querySelectorAll('a[href*="/jobs/search"]')].map(a => a.href)
"""
