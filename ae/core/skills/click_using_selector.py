import asyncio
import traceback
from typing import Annotated

from playwright.async_api import ElementHandle
from playwright.async_api import Page

from ae.core.playwright_manager import PlaywrightManager
from ae.utils.logger import logger


async def click(selector: Annotated[str, "The properly formed query selector string to identify the element for the click action. When \"mmid\" attribute is present, use it for the query selector."],
                wait_before_execution: Annotated[float, "Optional wait time in seconds before executing the click event logic.", float] = 0.0) -> Annotated[str, "A message indicating success or failure of the click."]:
    """
    Executes a click action on the element matching the given query selector string within the currently open web page.
    If there is no page open, it will raise a ValueError. An optional wait time can be specified before executing the click logic. Use this to wait for the page to load especially when the last action caused the DOM/Page to load.

    Parameters:
    - selector: The query selector string to identify the element for the click action.
    - wait_before_execution: Optional wait time in seconds before executing the click event logic. Defaults to 0.0 seconds.

    Returns:
    - Success if the click was successful, Appropropriate error message otherwise.
    """
    logger.info(f"Executing ClickElement with \"{selector}\" as the selector")

    # Initialize PlaywrightManager and get the active browser page
    browser_manager = PlaywrightManager(browser_type='chromium', headless=False)
    page = await browser_manager.get_current_page()

    if page is None: # type: ignore
        raise ValueError('No active page found. OpenURL command opens a new page.')

    await browser_manager.highlight_element(selector, True)
    result = await do_click(page, selector, wait_before_execution)
    await browser_manager.notify_user(result)
    return result


async def do_click(page: Page, selector: str, wait_before_execution: float) -> str:
    """
    Executes the click action on the element with the given selector within the provided page.

    Parameters:
    - page: The Playwright page instance.
    - selector: The query selector string to identify the element for the click action.
    - wait_before_execution: Optional wait time in seconds before executing the click event logic.

    Returns:
    - A message indicating success or failure of the click.
    """
    logger.info(f"Executing ClickElement with \"{selector}\" as the selector. Wait time before execution: {wait_before_execution} seconds.")

    # Wait before execution if specified
    if wait_before_execution > 0:
        await asyncio.sleep(wait_before_execution)

    # Wait for the selector to be present and ensure it's attached and visible. If timeout, try javascript click
    try:
        logger.info(f"Executing ClickElement with \"{selector}\" as the selector. Waiting for the element to be attached and visible.")

        element = await asyncio.wait_for(
            page.wait_for_selector(selector, state="attached", timeout=2000),
            timeout=2000
        )
        if element is None:
            raise ValueError(f"Element with selector: \"{selector}\" not found")

        logger.info(f"Element with selector: \"{selector}\" is attached. scrolling it into view if needed.")
        try:
            await element.scroll_into_view_if_needed(timeout=200)
            logger.info(f"Element with selector: \"{selector}\" is attached and scrolled into view. Waiting for the element to be visible.")
        except Exception:
            # If scrollIntoView fails, just move on, not a big deal
            pass

        try:
            await element.wait_for_element_state("visible", timeout=200)
            logger.info(f"Executing ClickElement with \"{selector}\" as the selector. Element is attached and visibe. Clicking the element.")
        except Exception:
            # If the element is not visible, try to click it anyway
            pass

        element_tag_name = await element.evaluate("element => element.tagName.toLowerCase()")

        if element_tag_name == "option":
            element_value = await element.get_attribute("value") # get the text that is in the value of the option
            parent_element = await element.evaluate_handle("element => element.parentNode")
            # await parent_element.evaluate(f"element => element.select_option(value=\"{element_value}\")")
            await parent_element.select_option(value=element_value) # type: ignore

            logger.info(f'Select menu option "{element_value}" selected')
            return f'Select menu option "{element_value}" selected'
        await element.focus()
        #Playwright click seems to fail more often than not, disabling it for now and just going with JS click
        #await perform_playwright_click(element, selector)
        await perform_javascript_click(page, selector)

        return f"Element with selector: \"{selector}\" clicked."
    except Exception as e:
        logger.error(f"Unable to click element with selector: \"{selector}\". Error: {e}")
        traceback.print_exc()
        return f"Unable to click element with selector: \"{selector}\" since the selector is invalid. Proceed by retrieving DOM again."


async def is_element_present(page: Page, selector: str) -> bool:
    """
    Checks if an element is present on the page.

    Parameters:
    - page: The Playwright page instance.
    - selector: The query selector string to identify the element.

    Returns:
    - True if the element is present, False otherwise.
    """
    element = await page.query_selector(selector)
    return element is not None


async def perform_playwright_click(element: ElementHandle, selector: str):
    """
    Performs a click action on the element using Playwright's click method.

    Parameters:
    - element: The Playwright ElementHandle instance representing the element to be clicked.
    - selector: The query selector string of the element.

    Returns:
    - None
    """
    logger.info(f"Performing first Step: Playwright Click on element with selector: {selector}")
    await element.click(force=False, timeout=200)


async def perform_javascript_click(page: Page, selector: str):
    """
    Performs a click action on the element using JavaScript.

    Parameters:
    - page: The Playwright page instance.
    - selector: The query selector string of the element.

    Returns:
    - None
    """
    js_code = """(selector) => {
        let element = document.querySelector(selector);

        if (!element) {
            console.log(`perform_javascript_click: Element with selector ${selector} not found`);
            return `perform_javascript_click: Element with selector ${selector} not found`;
        }

        if (element.tagName.toLowerCase() === "option") {
            let value = element.text;
            let parent = element.parentElement;

            parent.value = element.value; // Directly set the value if possible
            // Trigger change event if necessary
            let event = new Event('change', { bubbles: true });
            parent.dispatchEvent(event);

            console.log("Select menu option", value, "selected");
            return "Select menu option: "+ value+ " selected";
        }
        else {
            console.log("About to click selector", selector);
            // If the element is a link, make it open in the same tab
            if (element.tagName.toLowerCase() === "a") {
                element.target = "_self";
            }
            element.click();
            return "Executed JavaScript Click on element with selector: "+selector;
        }
    }"""
    try:
        logger.info(f"Executing JavaScript click on element with selector: {selector}")
        result:str = await page.evaluate(js_code, selector)
        logger.debug(f"Executed JavaScript Click on element with selector: {selector}")
        return result
    except Exception as e:
        logger.error(f"Error executing JavaScript click on element with selector: {selector}. Error: {e}")
        traceback.print_exc()

