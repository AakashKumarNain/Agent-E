import asyncio
import traceback
from dataclasses import dataclass
from typing import Annotated
from typing import List  # noqa: UP035

from playwright.async_api import Page

from ae.core.playwright_manager import PlaywrightManager
from ae.utils.logger import logger


@dataclass
class EnterTextEntry:
    """
    Represents an entry for text input.

    Attributes:
        query_selector (str): A valid DOM selector query. Use the mmid attribute.
        text (str): The text to enter in the element identified by the query_selector.
    """

    query_selector: str
    text: str

    def __getitem__(self, key: str) -> str:
        if key == "query_selector":
            return self.query_selector
        elif key == "text":
            return self.text
        else:
            raise KeyError(f"{key} is not a valid key")


async def custom_fill_element(page: Page, selector: str, text_to_enter: str):
    """
    Sets the value of a DOM element to a specified text without triggering keyboard input events.

    This function directly sets the 'value' property of a DOM element identified by the given CSS selector,
    effectively changing its current value to the specified text. This approach bypasses the need for
    simulating keyboard typing, providing a more efficient and reliable way to fill in text fields,
    especially in automated testing scenarios where speed and accuracy are paramount.

    Args:
        page (Page): The Playwright Page object representing the browser tab in which the operation will be performed.
        selector (str): The CSS selector string used to locate the target DOM element. The function will apply the
                        text change to the first element that matches this selector.
        text_to_enter (str): The text value to be set in the target element. Existing content will be overwritten.

    Example:
        await custom_fill_element(page, '#username', 'test_user')

    Note:
        This function does not trigger input-related events (like 'input' or 'change'). If application logic
        relies on these events being fired, additional steps may be needed to simulate them.
    """
    selector = f"{selector}"  # Ensures the selector is treated as a string
    await page.evaluate("""(inputParams) => {
        const selector = inputParams.selector;
        const text_to_enter = inputParams.text_to_enter;
        document.querySelector(selector).value = text_to_enter;
    }""", {"selector": selector, "text_to_enter": text_to_enter})

async def entertext(entry: Annotated[EnterTextEntry, "An object containing 'query_selector' (DOM selector query using mmid attribute) and 'text' (text to enter on the element)."]) -> Annotated[str, "Explanation of the outcome of this operation."]:
    """
    Enters text into a DOM element identified by a CSS selector.

    This function enters the specified text into a DOM element identified by the given CSS selector.
    It uses the Playwright library to interact with the browser and perform the text entry operation.
    The function supports both direct setting of the 'value' property and simulating keyboard typing.

    Args:
        entry (EnterTextEntry): An object containing 'query_selector' (DOM selector query using mmid attribute)
                                and 'text' (text to enter on the element).

    Returns:
        str: Explanation of the outcome of this operation.

    Example:
        entry = EnterTextEntry(query_selector='#username', text='test_user')
        result = await entertext(entry)

    Note:
        - The 'query_selector' should be a valid CSS selector that uniquely identifies the target element.
        - The 'text' parameter specifies the text to be entered into the element.
        - The function uses the PlaywrightManager to manage the browser instance.
        - If no active page is found, an error message is returned.
        - The function internally calls the 'do_entertext' function to perform the text entry operation.
        - The 'do_entertext' function applies a pulsating border effect to the target element during the operation.
        - The 'use_keyboard_fill' parameter in 'do_entertext' determines whether to simulate keyboard typing or not.
        - If 'use_keyboard_fill' is set to True, the function uses the 'page.keyboard.type' method to enter the text.
        - If 'use_keyboard_fill' is set to False, the function uses the 'custom_fill_element' method to enter the text.
    """
    logger.info(f"Entering text: {entry}")
    query_selector: str = entry['query_selector']
    text_to_enter: str = entry['text']

    # Create and use the PlaywrightManager
    browser_manager = PlaywrightManager(browser_type='chromium', headless=False)
    page = await browser_manager.get_current_page()
    if page is None: # type: ignore
        return "Error: No active page found. OpenURL command opens a new page."

    await browser_manager.highlight_element(query_selector, True)
    result = await do_entertext(page, query_selector, text_to_enter)
    await browser_manager.notify_user(result)
    return result


async def do_entertext(page: Page, selector: str, text_to_enter: str, use_keyboard_fill: bool=False):
    """
    Performs the text entry operation on a DOM element.

    This function performs the text entry operation on a DOM element identified by the given CSS selector.
    It applies a pulsating border effect to the element during the operation for visual feedback.
    The function supports both direct setting of the 'value' property and simulating keyboard typing.

    Args:
        page (Page): The Playwright Page object representing the browser tab in which the operation will be performed.
        selector (str): The CSS selector string used to locate the target DOM element.
        text_to_enter (str): The text value to be set in the target element. Existing content will be overwritten.
        use_keyboard_fill (bool, optional): Determines whether to simulate keyboard typing or not.
                                            Defaults to False.

    Returns:
        str: Explanation of the outcome of this operation.

    Example:
        result = await do_entertext(page, '#username', 'test_user')

    Note:
        - The 'use_keyboard_fill' parameter determines whether to simulate keyboard typing or not.
        - If 'use_keyboard_fill' is set to True, the function uses the 'page.keyboard.type' method to enter the text.
        - If 'use_keyboard_fill' is set to False, the function uses the 'custom_fill_element' method to enter the text.
    """
    try:
        logger.debug(f"Looking for selector {selector} to enter text: {text_to_enter}")

        elem = await page.query_selector(selector)

        if elem is None:
            return f"Error: Selector {selector} not found. Unable to continue."

        logger.info(f"Found selector {selector} to enter text")

        if use_keyboard_fill:
            await elem.focus()
            logger.debug(f"Focused element with selector {selector} to enter text")
            await page.keyboard.type(text_to_enter, delay=2)
        else:
            await custom_fill_element(page, selector, text_to_enter)
        logger.info(f"Success. Text \"{text_to_enter}\" set successfully in the element with selector {selector}")
        await elem.focus()
        await page.keyboard.type(" ") # some html pages can have placeholders that only disappear upon keyboard input
        await asyncio.sleep(1)

        return f"Success. Text \"{text_to_enter}\" set successfully in the element with selector {selector}"

    except Exception as e:
        traceback.print_exc()
        return f"Error entering text in selector {selector}. Error: {str(e)}"


async def bulk_enter_text(
    entries: Annotated[List[dict[str, str]], "List of objects, each containing 'query_selector' and 'text'."]  # noqa: UP006
) -> Annotated[List[dict[str, str]], "List of dictionaries, each containing 'query_selector' and the result of the operation."]:  # noqa: UP006
    """
    Enters text into multiple DOM elements using a bulk operation.

    This function enters text into multiple DOM elements using a bulk operation.
    It takes a list of dictionaries, where each dictionary contains a 'query_selector' and 'text' pair.
    The function internally calls the 'entertext' function to perform the text entry operation for each entry.

    Args:
        entries: List of objects, each containing 'query_selector' and 'text'.

    Returns:
        List of dictionaries, each containing 'query_selector' and the result of the operation.

    Example:
        entries = [
            {"query_selector": "#username", "text": "test_user"},
            {"query_selector": "#password", "text": "test_password"}
        ]
        results = await bulk_enter_text(entries)

    Note:
        - Each entry in the 'entries' list should be a dictionary with 'query_selector' and 'text' keys.
        - The result is a list of dictionaries, where each dictionary contains the 'query_selector' and the result of the operation.
    """

    results: List[dict[str, str]] = []  # noqa: UP006
    logger.info("Executing bulk Enter Text Command")
    for entry in entries:
        query_selector = entry['query_selector']
        text_to_enter = entry['text']
        logger.info(f"Entering text: {text_to_enter} in element with selector: {query_selector}")
        result = await entertext(EnterTextEntry(query_selector=query_selector, text=text_to_enter))

        results.append({"query_selector": query_selector, "result": result})

    return results
