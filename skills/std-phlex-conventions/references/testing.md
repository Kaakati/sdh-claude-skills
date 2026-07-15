# Testing Phlex Components

Load-bearing rules restated (this file is self-contained):

- Unit-test components with `Phlex::Testing::ViewHelper` (or `Phlex::Testing::Rails::ViewHelper`
  when the component uses Rails helpers such as routes or `turbo_frame_tag`).
- Test the rendered **output**, not the component's private methods.
- Follow AAA (Arrange, Act, Assert). One concept per test.
- Name tests `should [expected behavior] when [condition]`.

Setup:

```ruby
# spec/rails_helper.rb
require "phlex/testing/rails/view_helper"

RSpec.configure do |config|
  config.include Phlex::Testing::Rails::ViewHelper, type: :component
end
```

`render` returns the HTML string. Parse it with Nokogiri when asserting on structure.

---

## Decision: asserting on output — string match or DOM?

Bad — brittle full-string equality that breaks on any class reorder:

```ruby
it "renders a button" do
  output = render Components::Atoms::Button.new(label: "Save")
  expect(output).to eq(
    '<button type="button" class="inline-flex items-center justify-center rounded-md ' \
    'font-medium transition-colors bg-primary text-primary-foreground h-10 px-4">Save</button>'
  )
end
```

Good — assert on the things that carry meaning:

```ruby
# spec/components/atoms/button_spec.rb
require "rails_helper"

RSpec.describe Components::Atoms::Button, type: :component do
  def button_in(html) = Nokogiri::HTML5.fragment(html).at_css("button")

  it "should render the label inside a button element when given a label" do
    html = render described_class.new(label: "Save")

    button = button_in(html)
    expect(button.text).to eq("Save")
    expect(button[:type]).to eq("button")
  end

  it "should apply primary token classes when variant is primary" do
    html = render described_class.new(label: "Save", variant: :primary)

    expect(button_in(html)[:class]).to include("bg-primary", "text-primary-foreground")
  end

  it "should apply destructive token classes when variant is destructive" do
    html = render described_class.new(label: "Delete", variant: :destructive)

    classes = button_in(html)[:class]
    expect(classes).to include("bg-error")
    expect(classes).not_to include("bg-primary")
  end
end
```

---

## Decision: testing every variant combination

Bad — one test that asserts eight things, so a failure tells you nothing:

```ruby
it "renders variants" do
  expect(render(described_class.new(label: "a", variant: :primary))).to include("bg-primary")
  expect(render(described_class.new(label: "a", variant: :secondary))).to include("bg-secondary")
  expect(render(described_class.new(label: "a", size: :sm))).to include("h-8")
  expect(render(described_class.new(label: "a", size: :lg))).to include("h-12")
end
```

Good — a table-driven spec; each case reports independently:

```ruby
RSpec.describe Components::Atoms::Button, type: :component do
  describe "variant axis" do
    {
      primary: "bg-primary",
      secondary: "bg-secondary",
      destructive: "bg-error",
      outline: "border-input",
      ghost: "hover:bg-accent"
    }.each do |variant, expected_class|
      it "should apply #{expected_class} when variant is #{variant}" do
        html = render described_class.new(label: "Go", variant: variant)

        expect(html).to include(expected_class)
      end
    end
  end

  describe "size axis" do
    { sm: "h-8", md: "h-10", lg: "h-12" }.each do |size, expected_class|
      it "should apply #{expected_class} when size is #{size}" do
        html = render described_class.new(label: "Go", size: size)

        expect(html).to include(expected_class)
      end
    end
  end

  it "should apply the default variant and size when neither is given" do
    html = render described_class.new(label: "Go")

    expect(html).to include("bg-primary", "h-10")
  end
end
```

---

## Decision: testing a component that yields a block

Bad — asserting the block ran by checking the component's own markup only:

```ruby
it "renders a card" do
  expect(render(Components::Atoms::Card.new)).to include("rounded-lg")
end
```

Good — pass a block and assert the child content lands inside the right element:

```ruby
RSpec.describe Components::Atoms::Card, type: :component do
  it "should render block content inside the card container when given a block" do
    html = render(described_class.new) { "Inner content" }

    card = Nokogiri::HTML5.fragment(html).at_css("div")
    expect(card.text).to include("Inner content")
    expect(card[:class]).to include("bg-card")
  end

  it "should render nested components when the block renders a component" do
    html = render(described_class.new) do
      render Components::Atoms::Badge.new(label: "New")
    end

    expect(Nokogiri::HTML5.fragment(html).at_css("div > span").text).to eq("New")
  end
end
```

---

## Decision: testing composition (a molecule renders its atoms)

Test the **output contract**, not that `render` was called — mocking child components couples the
spec to internals and stops catching real markup regressions.

Bad:

```ruby
it "renders a button" do
  expect(Components::Atoms::Button).to receive(:new).with(hash_including(label: "Search"))
  render Components::Molecules::SearchForm.new(action: "/search")
end
```

Good:

```ruby
RSpec.describe Components::Molecules::SearchForm, type: :component do
  subject(:html) { render described_class.new(action: "/search", query: "boots") }

  let(:doc) { Nokogiri::HTML5.fragment(html) }

  it "should submit to the given action via GET when rendered" do
    form = doc.at_css("form")

    expect(form[:action]).to eq("/search")
    expect(form[:method]).to eq("get")
  end

  it "should prefill the input when a query is given" do
    expect(doc.at_css("input[name='q']")[:value]).to eq("boots")
  end

  it "should render a submit button when rendered" do
    expect(doc.at_css("button[type='submit']").text).to eq("Search")
  end

  it "should expose a search landmark when rendered" do
    expect(doc.at_css("form")[:role]).to eq("search")
  end
end
```

---

## Decision: testing Stimulus wiring

The rendered `data-*` attributes are the component's contract with the JS controller. Assert them
explicitly — a typo in `data: { dropdown_taget: "menu" }` is otherwise silent.

```ruby
RSpec.describe Components::Organisms::Dropdown, type: :component do
  subject(:doc) { Nokogiri::HTML5.fragment(render(described_class.new(label: "Menu")) { "Item" }) }

  it "should scope the dropdown controller to the component root when rendered" do
    expect(doc.at_css("div")["data-controller"]).to eq("dropdown")
  end

  it "should bind the toggle action to the trigger when rendered" do
    expect(doc.at_css("[data-dropdown-target='trigger']")["data-action"]).to eq("click->dropdown#toggle")
  end

  it "should mark the menu element as a target when rendered" do
    expect(doc.at_css("[data-dropdown-target='menu']")).to be_present
  end

  it "should start with the menu hidden when rendered" do
    expect(doc.at_css("[data-dropdown-target='menu']")[:hidden]).to be_present
  end

  it "should report collapsed state to assistive tech when rendered" do
    expect(doc.at_css("[data-dropdown-target='trigger']")["aria-expanded"]).to eq("false")
  end
end
```

---

## Decision: testing a page view

A page takes data from the controller, so unit-test it with plain doubles or factories — no HTTP.

```ruby
RSpec.describe Views::Articles::Index, type: :component do
  let(:articles) { create_list(:article, 3) }

  it "should render one card per article when articles are present" do
    html = render described_class.new(articles: articles)

    expect(Nokogiri::HTML5.fragment(html).css("article").size).to eq(3)
  end

  it "should render the empty state when there are no articles" do
    html = render described_class.new(articles: [])

    expect(html).to include("No articles yet")
    expect(Nokogiri::HTML5.fragment(html).css("article")).to be_empty
  end
end
```

Pair one request spec per page to prove the controller wires the view correctly — do not duplicate
the markup assertions there:

```ruby
RSpec.describe "Articles", type: :request do
  it "should render the index view when articles exist" do
    create(:article, title: "Hello Phlex")

    get articles_path

    expect(response).to have_http_status(:ok)
    expect(response.body).to include("Hello Phlex")
  end
end
```

---

## Decision: what NOT to test

| Do not test | Why | Test instead |
|---|---|---|
| Private methods (`send(:button_classes)`) | Implementation detail | Rendered `class` attribute |
| Exact full HTML strings | Breaks on any reorder | Specific elements/attributes via Nokogiri |
| That `render` was called on a child | Couples to internals | The child's markup in the output |
| Tailwind's own behavior | Not your code | Your token class names appear |
| Stimulus controller logic | Belongs in a JS test | That the `data-*` contract is emitted |
