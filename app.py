import os
import subprocess
import tempfile
import zipfile
import streamlit as st
from playwright.sync_api import sync_playwright

# Page configuration
st.set_page_config(
    page_title="AI Reference Page Printer Agent",
    page_icon="📥",
    layout="wide",
)

# Automatically download Playwright Chromium binary on startup if missing
@st.cache_resource
def install_playwright_browsers():
    try:
        # Try running playwright install
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception:
        try:
            os.system("python -m playwright install chromium")
        except Exception as e:
            st.error(f"Failed to automatically install Playwright browser: {e}")

install_playwright_browsers()

def process_links(urls, output_format, export_type):
    """Core agent logic to open links and print/save them like Chrome."""
    temp_dir = tempfile.mkdtemp()
    results = []
    
    try:
        with sync_playwright() as p:
            # Launch headless browser mimicking Chrome
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            total = len(urls)
            
            for i, url in enumerate(urls):
                url = url.strip()
                if not url:
                    continue
                    
                status_text.text(f"Agent processing ({i+1}/{total}): {url}")
                page = context.new_page()
                
                try:
                    # Navigate and wait for network activity to settle
                    page.goto(url, timeout=30000, wait_until="networkidle")
                    
                    # Clean filename from URL
                    safe_name = "".join([c if c.isalnum() else "_" for c in url.split("//")[-1]])[:50]
                    
                    if output_format == "PDF":
                        file_path = os.path.join(temp_dir, f"{safe_name}.pdf")
                        page.pdf(path=file_path, format="A4", print_background=True)
                    else:
                        file_path = os.path.join(temp_dir, f"{safe_name}.html")
                        html_content = page.content()
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(html_content)
                    
                    results.append({"url": url, "path": file_path, "status": "Success"})
                except Exception as e:
                    results.append({"url": url, "path": None, "status": f"Failed: {str(e)}"})
                finally:
                    page.close()
                    
                progress_bar.progress((i + 1) / total)
                
            browser.close()
        status_text.text("Processing complete!")
    except Exception as launch_error:
        st.error(
            f"Could not launch browser. Ensure `packages.txt` is present in your repository root. Details: {launch_error}"
        )
        
    return temp_dir, results

# Streamlit UI Layout
st.title("📥 AI Agent: Reference Page Printer")
st.markdown(
    "Provide a list of reference links below. The agent will browse each link, "
    "render the page dynamically (just like Chrome), and compile them into downloadable files."
)

with st.form("agent_form"):
    urls_input = st.text_area(
        "Paste your links here (one URL per line):",
        placeholder="https://example.com/article-1\nhttps://example.com/article-2",
        height=150
    )
    
    col1, col2 = st.columns(2)
    with col1:
        output_format = st.selectbox("Output Format", ["PDF", "HTML"])
    with col2:
        export_mode = st.selectbox("Download Package Type", ["Individual Files", "ZIP Archive"])
        
    submit_btn = st.form_submit_button("Run Agent & Print Pages")

if submit_btn:
    urls = [u.strip() for u in urls_input.split("\n") if u.strip()]
    
    if not urls:
        st.warning("Please enter at least one valid URL.")
    else:
        st.info(f"Agent initialized. Processing {len(urls)} links...")
        temp_dir, results = process_links(urls, output_format, export_mode)
        
        if results:
            st.success("All tasks processed successfully!")
            
            # Display summary table
            st.subheader("Execution Summary")
            for res in results:
                if res["status"] == "Success":
                    st.write(f"✅ **{res['url']}** -> Saved successfully")
                else:
                    st.write(f"❌ **{res['url']}** -> Error: {res['status']}")
                    
            # Provide download options
            successful_files = [r["path"] for r in results if r["path"] and os.path.exists(r["path"])]
            
            if successful_files:
                if export_mode == "ZIP Archive":
                    zip_path = os.path.join(temp_dir, "printed_references.zip")
                    with zipfile.ZipFile(zip_path, "w") as zipf:
                        for file in successful_files:
                            zipf.write(file, os.path.basename(file))
                    
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="📦 Download All as ZIP",
                            data=f,
                            file_name="printed_references.zip",
                            mime="application/zip"
                        )
                else:
                    st.subheader("Download Individual Files")
                    for file in successful_files:
                        filename = os.path.basename(file)
                        with open(file, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Download {filename}",
                                data=f,
                                file_name=filename,
                                mime="application/pdf" if output_format == "PDF" else "text/html"
                            )
