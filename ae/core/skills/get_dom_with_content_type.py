
import os
import time
from typing import Annotated
from typing import Any

from ae.config import SOURCE_LOG_FOLDER_PATH
from ae.core.playwright_manager import PlaywrightManager
from ae.utils.dom_helper import wait_for_non_loading_dom_state
from ae.utils.get_detailed_accessibility_tree import do_get_accessibility_info
from ae.utils.logger import logger


async def get_dom_with_content_type(
    content_type: Annotated[str, "The type of content to extract: 'text_only': Extracts the innerText of the highest element in the document and responds with text, or 'input_fields': Extracts the interactive elements in the dom."]
    ) -> Annotated[dict[str, Any] | str | None, "The output based on the specified content type."]:
    """
    Retrieves and processes the DOM of the active page in a browser instance based on the specified content type.

    Parameters
    ----------
    content_type : str
        The type of content to extract. Possible values are:
        - 'text_only': Extracts the innerText of the highest element in the document and responds with text.
        - 'input_fields': Extracts the interactive elements in the DOM and responds with a JSON object.
        - 'all_fields': Extracts all the fields in the DOM and responds with a JSON object.

    Returns
    -------
    dict[str, Any] | str | None
        The processed content based on the specified content type. This could be:
        - A JSON object for 'input_fields' with just inputs.
        - Plain text for 'text_only'.
        - A minified DOM represented as a JSON object for 'all_fields'.

    Raises
    ------
    ValueError
        If an unsupported content_type is provided.
    """

    logger.info(f"Executing Get DOM Command based on content_type: {content_type}")
    start_time = time.time()
    # Create and use the PlaywrightManager
    browser_manager = PlaywrightManager(browser_type='chromium', headless=False)
    page = await browser_manager.get_current_page()
    if page is None: # type: ignore
        raise ValueError('No active page found. OpenURL command opens a new page.')

    extracted_data = None
    await wait_for_non_loading_dom_state(page, 2000) # wait for the DOM to be ready, non loading means external resources do not need to be loaded
    user_success_message = ""
    if content_type == 'all_fields':
        logger.debug('Fetching DOM for all_fields')
        extracted_data = await do_get_accessibility_info(page, only_input_fields=False)
        user_success_message = "Fetched all the fields in the DOM"
    elif content_type == 'input_fields':
        logger.debug('Fetching DOM for input_fields')
        extracted_data = await do_get_accessibility_info(page, only_input_fields=True)
        user_success_message = "Fetched only input fields in the DOM"
    elif content_type == 'text_only':
        # Extract text from the body or the highest-level element
        logger.debug('Fetching DOM for text_only')
        text_content = await page.evaluate("""() => document?.body?.innerText || document?.documentElement?.innerText || "" """)
        with open(os.path.join(SOURCE_LOG_FOLDER_PATH, 'text_only_dom.txt'), 'w',  encoding='utf-8') as f:
            f.write(text_content)
        extracted_data = text_content
        user_success_message = "Fetched the text content of the DOM"
    else:
        raise ValueError(f"Unsupported content_type: {content_type}")

    elapsed_time = time.time() - start_time
    logger.info(f"Get DOM Command executed in {elapsed_time} seconds")
    await browser_manager.notify_user(user_success_message)

    return extracted_data


