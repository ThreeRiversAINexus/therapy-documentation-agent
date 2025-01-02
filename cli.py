#!/usr/bin/env python3
import sys
import argparse
import fileinput
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.panel import Panel
from rich import print as rprint
from bot.core import TherapyDocumentationBot

console = Console()

class TherapyDocCLI:
    def __init__(self, base_url="http://localhost:5000", interactive=False):
        """Initialize CLI with bot in production mode"""
        self.chatbot = TherapyDocumentationBot(test_mode=False)
        self.interactive = interactive

    def start_chat(self):
        """Start a new chat session"""
        try:
            response = self.chatbot.start_documentation()
            message = response.get("response", "Hey! What's up? How have you been doing?")
            self._display_bot_message(message)
            return message
        except Exception as e:
            console.print(f"[red]Error starting chat: {e}[/red]")
            sys.exit(1)

    def send_message(self, message, quiet=False, interactive=None):
        """Send a message and get response"""
        try:
            # Add mode to message for the agent
            mode_message = f"[{'interactive' if (interactive if interactive is not None else self.interactive) else 'non-interactive'} mode] {message}"
            response = self.chatbot.process_message(mode_message)
            
            if not quiet:
                # Display bot response
                bot_message = response.get("response", "")
                if isinstance(bot_message, dict) and 'response' in bot_message:
                    bot_message = bot_message['response']
                elif isinstance(bot_message, str):
                    bot_message = bot_message
                else:
                    bot_message = str(bot_message)
                
                self._display_bot_message(bot_message)
                
                # If we have a current category, show its documentation
                if self.chatbot.tools.current_category:
                    try:
                        summary = self.chatbot.tools.get_category_summary(
                            category_id=self.chatbot.tools.current_category
                        )
                        self._display_documentation({
                            "category": self.chatbot.tools.current_category,
                            "data": {
                                "sections": summary.get('sections', {}),
                                "next_steps": summary.get('next_steps', '')
                            },
                            "notes": summary.get('notes', '')
                        })
                    except Exception as e:
                        print(f"Error displaying documentation: {e}")
            
            return response
                
        except Exception as e:
            console.print(f"[red]Error sending message: {e}[/red]")
            return None

    def get_categories(self):
        """Get available categories"""
        try:
            return self.chatbot.tools.get_categories()
        except Exception as e:
            console.print(f"[red]Error getting categories: {e}[/red]")
            return []

    def _display_bot_message(self, message):
        """Display bot message in a nice panel"""
        console.print(Panel(
            str(message),  # Ensure message is a string
            title="Bot",
            border_style="blue",
            padding=(1, 2)
        ))

    def _display_documentation(self, doc):
        """Display documentation data in a nice format"""
        if not doc.get("category"):
            return
            
        console.print("\n[bold blue]Documentation Updated:[/bold blue]")
        console.print(f"Category: {doc['category']}")
        
        if 'data' in doc:
            if doc['data'].get('sections'):
                console.print("\n[bold]Observations:[/bold]")
                for section, observations in doc['data']['sections'].items():
                    if observations and len(observations) > 0:
                        console.print(f"\n[bold]{section}:[/bold]")
                        for entry in observations:
                            # Format timestamp to be more readable
                            timestamp = entry['timestamp'].replace('T', ' ').split('.')[0]
                            console.print(f"[{timestamp}] {entry['observation']}")
            
            if doc['data'].get('next_steps'):
                console.print("\n[bold]Next Steps:[/bold]")
                console.print(doc['data']['next_steps'])
        
        if doc.get('notes'):
            console.print("\n[bold]Notes:[/bold]")
            console.print(doc['notes'])

    def save_documentation(self, category, observations="", next_steps="", notes=""):
        """Save documentation for a category"""
        try:
            # Get category info to know available sections
            categories = {cat['id']: cat for cat in self.get_categories()}
            if category not in categories:
                raise ValueError(f"Invalid category: {category}")
            
            # Parse observations into sections
            if observations:
                sections = categories[category].get('sections', [])
                if len(sections) == 1:
                    # If only one section, use all observations for it
                    self.chatbot.tools.set_category_section_observations(
                        category_id=category,
                        section_name=sections[0],
                        observations=observations
                    )
                else:
                    # Try to parse sections from the observations text
                    section_data = {}
                    current_section = None
                    
                    for line in observations.split('\n'):
                        # Check if line starts with a section name
                        is_section = False
                        for section in sections:
                            if line.lower().startswith(section.lower() + ':'):
                                current_section = section
                                section_data[section] = line[len(section) + 1:].strip()
                                is_section = True
                                break
                        
                        if not is_section and current_section:
                            # Append to current section
                            section_data[current_section] += '\n' + line
                    
                    # Save each section's observations
                    for section, obs in section_data.items():
                        self.chatbot.tools.set_category_section_observations(
                            category_id=category,
                            section_name=section,
                            observations=obs.strip()
                        )
            
            if next_steps:
                self.chatbot.tools.set_category_next_steps(category, next_steps)
            if notes:
                self.chatbot.tools.add_category_notes(category, notes)
            console.print("[green]Documentation saved successfully![/green]")
        except Exception as e:
            console.print(f"[red]Error saving documentation: {e}[/red]")

def interactive_mode(cli):
    """Run in interactive mode"""
    # Start chat session
    cli.start_chat()
    
    # Main chat loop
    while True:
        try:
            # Get user input
            message = Prompt.ask("\nYou")
            
            # Handle special commands
            if message.lower() in ['quit', 'exit', 'bye']:
                console.print("[yellow]Goodbye![/yellow]")
                break
            elif message.lower() == 'categories':
                categories = cli.get_categories()
                console.print("\n[bold]Available Categories:[/bold]")
                for cat in categories:
                    console.print(f"- {cat['name']} (id: {cat['id']})")
                continue
            elif message.lower().startswith('save '):
                # Format: save <category_id> <observations> | <next_steps> | <notes>
                parts = message[5:].split('|')
                if len(parts) < 1:
                    console.print("[red]Invalid format. Use: save <category_id> <observations> | <next_steps> | <notes>[/red]")
                    continue
                
                category_parts = parts[0].strip().split(' ', 1)
                if len(category_parts) < 2:
                    console.print("[red]Invalid format. Use: save <category_id> <observations> | <next_steps> | <notes>[/red]")
                    continue
                
                category = category_parts[0]
                observations = category_parts[1]
                next_steps = parts[1].strip() if len(parts) > 1 else ""
                notes = parts[2].strip() if len(parts) > 2 else ""
                
                cli.save_documentation(category, observations, next_steps, notes)
                continue
            
            # Display user message
            console.print(Panel(
                message,
                title="You",
                border_style="green",
                padding=(1, 2)
            ))
            
            # Send message and get response
            cli.send_message(message)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

def batch_mode(cli, input_file=None, csv_mode=False):
    """Run in batch mode, reading from stdin or file"""
    # Start chat session quietly
    cli.start_chat()
    
    if csv_mode:
        import csv
        with open(input_file, 'r') as f:
            reader = csv.reader(f)
            messages = [row[0] for row in reader if row]  # Get first column
    else:
        messages = [line.strip() for line in fileinput.input(files=input_file if input_file else ['-']) if line.strip()]
    
    for message in messages:
        # Show the input message
        console.print(Panel(
            message,
            title="Input",
            border_style="yellow",
            padding=(1, 2)
        ))
        
        # Process the message
        response = cli.send_message(message, quiet=False)
        
        # Add a separator
        console.print("=" * 80 + "\n")
        
        # If in interactive mode, ask if user wants to continue
        if not input_file:
            if not Prompt.ask("Continue? [y/n]", default="y").lower().startswith('y'):
                break

def get_history_summary(cli, days=14):
    """Get summary of documentation from the last N days"""
    categories = cli.get_categories()
    summaries = []
    
    for category in categories:
        try:
            summary = cli.chatbot.tools.get_category_summary(category_id=category['id'])
            if summary and summary.get('sections'):
                has_content = False
                category_lines = []
                
                # Start with category header
                category_lines.append(f"\n[bold]{category['name']}[/bold]")
                category_lines.append("\nObservations:")
                
                # Add sections with observations
                for section, observations in summary['sections'].items():
                    if observations and len(observations) > 0:
                        has_content = True
                        category_lines.append(f"\n[bold]{section}:[/bold]")
                        for entry in observations:
                            timestamp = entry['timestamp'].replace('T', ' ').split('.')[0]
                            category_lines.append(f"[{timestamp}] {entry['observation']}")
                
                # Add next steps and notes if they exist
                if summary.get('next_steps'):
                    has_content = True
                    category_lines.append("\nNext Steps:")
                    category_lines.append(summary['next_steps'])
                if summary.get('notes'):
                    has_content = True
                    category_lines.append("\nNotes:")
                    category_lines.append(summary['notes'])
                
                # Only add category if it has content
                if has_content:
                    summaries.extend(category_lines)
        except Exception as e:
            console.print(f"[red]Error getting summary for {category['name']}: {e}[/red]")
    
    if summaries:
        console.print("\n[bold blue]Documentation Summary (Last 2 Weeks):[/bold blue]")
        console.print("\n".join(summaries))
    else:
        console.print("[yellow]No documentation found for the specified period.[/yellow]")

def single_message_mode(cli, message):
    """Process a single message and exit"""
    # Start chat session
    cli.start_chat()
    
    # Display user message
    console.print(Panel(
        message,
        title="You",
        border_style="green",
        padding=(1, 2)
    ))
    
    # Send message and get response
    cli.send_message(message)

def main():
    parser = argparse.ArgumentParser(description='Therapy Documentation CLI')
    parser.add_argument('message', nargs='?', help='Single message to process')
    parser.add_argument('--batch', '-b', help='Process messages from file (use - for stdin)', metavar='FILE')
    parser.add_argument('--csv', '-c', help='Process messages from CSV file (first column)', metavar='FILE')
    parser.add_argument('--summary', '-s', action='store_true', help='Show documentation summary for last 2 weeks')
    parser.add_argument('--url', default='http://localhost:5000', help='Server URL')
    parser.add_argument('--interactive', '-i', action='store_true', help='Continue in interactive mode after processing message')
    args = parser.parse_args()

    cli = TherapyDocCLI(base_url=args.url, interactive=bool(args.interactive))

    if args.summary:
        # Summary mode
        get_history_summary(cli)
    elif args.csv:
        # CSV mode
        batch_mode(cli, args.csv, csv_mode=True)
    elif args.batch:
        # Batch mode
        batch_mode(cli, args.batch if args.batch != '-' else None)
    elif args.message:
        # Single message mode
        single_message_mode(cli, args.message)
        
        # Continue in interactive mode if flag is set
        if args.interactive:
            interactive_mode(cli)
    else:
        # Interactive mode
        console.print("[bold blue]Therapy Documentation CLI[/bold blue]")
        console.print("Type 'categories' to list available categories")
        console.print("Type 'save <category_id> <observations> | <next_steps> | <notes>' to save documentation")
        console.print("Type 'summary' to see documentation summary")
        console.print("Type 'quit' to exit")
        console.print("=" * 50)
        interactive_mode(cli)

if __name__ == "__main__":
    main()
