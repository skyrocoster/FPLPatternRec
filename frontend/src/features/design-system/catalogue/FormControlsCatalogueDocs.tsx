import { FamilyPage } from "./FamilyPage";

/** Reference prose and links kept separate from the interactive catalogue stories. */
export function FormControlsCatalogueDocs() {
  return (
    <FamilyPage
      family="Actions and Form Controls"
      intro={
        <>
          The shared controls in features/design-system and their Base UI behavior layer. Existing
          production coverage lives in the Production/Design System stories; the demos below fill
          the gaps for controls that previously had no stories. All form controls compose Base UI
          primitives (no native-only fallbacks), and validation state stays outside the controls.
        </>
      }
      caution="CheckboxGroup provides the shared grouped-checkbox presentation. There is no standalone Toolbar wrapper in the retained component set."
      sections={[
        {
          heading: "Button",
          body: (
            <>
              Token-driven button built on the Base UI headless Button primitive. Three variants
              (primary, secondary, ghost) across two sizes (md, sm), plus the disabled state.
              Interactive by nature; the existing story shows the full matrix.
            </>
          ),
          links: [
            {
              label: "Production/Design System/Components/Button — Variant Matrix",
              storyId: "production-design-system-components-button--variant-matrix",
            },
          ],
        },
        {
          heading: "Field",
          body: (
            <>
              Presentation-only field scaffolding around the Base UI Field: label (with an optional
              required mark), optional description, optional error text, and disabled/invalid
              wiring. It owns no validation timing or form state; pass the error and invalid props
              from the caller. The Base Field association connects the label, description, and error
              to the child control for accessibility.
            </>
          ),
        },
        {
          heading: "TextInput",
          body: (
            <>
              Base UI Input wrapped in a shared frame with optional leading and trailing slots and
              an invalid state. Standard input types (text, search, email, url, tel, password) are
              supported; combine with Field for labels, descriptions, and errors.
            </>
          ),
        },
        {
          heading: "Select, Combobox, Autocomplete",
          body: (
            <>
              Dropdown controls sharing one presentation: Select for plain choice lists, Combobox
              for filterable search with typed input and a clear action, Autocomplete for free text
              backed by suggestions. All three accept loading (options hidden with a loading
              message) and empty states, and the popup options can be rich compositions via
              DropdownOptionContent. Note the Base UI popup renders in a portal, so popup styling is
              visible only while a popup is open. Provide ariaLabel on every control: the controls
              rely on it for the accessible name.
            </>
          ),
        },
        {
          heading: "RadioGroup",
          body: (
            <>
              Base UI Radio Group with two appearance names: segmented (inline toggle bar for a
              small choice set) and stacked (vertical list that can carry a second description
              line). Provide the required ariaLabel (the group's accessible name). The group is
              required by default (required=true) and options may be individually disabled.
            </>
          ),
        },
        {
          heading: "Advanced Base UI form controls",
          body: "Reusable production wrappers now cover CheckboxGroup, Fieldset, Form, NumberField, OtpField, Slider, Switch, Toggle, and ToggleGroup. Their stories show the basic flexible API; feature-specific copy, bounds, values, and form validation remain caller-owned.",
          links: [
            {
              label: "Advanced Form Controls — Checkbox Group",
              storyId:
                "production-design-system-base-ui-advanced-form-controls--checkbox-group-example",
            },
            {
              label: "Advanced Form Controls — Fieldset",
              storyId: "production-design-system-base-ui-advanced-form-controls--fieldset-example",
            },
            {
              label: "Advanced Form Controls — Form",
              storyId: "production-design-system-base-ui-advanced-form-controls--form-example",
            },
            {
              label: "Advanced Form Controls — Number Field",
              storyId:
                "production-design-system-base-ui-advanced-form-controls--number-field-example",
            },
            {
              label: "Advanced Form Controls — OTP Field",
              storyId: "production-design-system-base-ui-advanced-form-controls--otp-field-example",
            },
            {
              label: "Advanced Form Controls — Slider",
              storyId: "production-design-system-base-ui-advanced-form-controls--slider-example",
            },
            {
              label: "Advanced Form Controls — Switch",
              storyId: "production-design-system-base-ui-advanced-form-controls--switch-example",
            },
            {
              label: "Advanced Form Controls — Toggle",
              storyId: "production-design-system-base-ui-advanced-form-controls--toggle-example",
            },
            {
              label: "Advanced Form Controls — Toggle Group",
              storyId:
                "production-design-system-base-ui-advanced-form-controls--toggle-group-example",
            },
          ],
        },
        {
          heading: "Demos",
          body: "Rendered with the actual production components and the FormControls styles.",
          links: [
            {
              label: "Field States",
              storyId: "reference-catalogue-actions-and-form-controls--field-states",
            },
            {
              label: "TextInput States",
              storyId: "reference-catalogue-actions-and-form-controls--text-input-states",
            },
            {
              label: "Select States",
              storyId: "reference-catalogue-actions-and-form-controls--select-states",
            },
            {
              label: "Select Loading and Empty",
              storyId: "reference-catalogue-actions-and-form-controls--select-loading-and-empty",
            },
            {
              label: "Combobox States",
              storyId: "reference-catalogue-actions-and-form-controls--combobox-states",
            },
            {
              label: "Autocomplete States",
              storyId: "reference-catalogue-actions-and-form-controls--autocomplete-states",
            },
            {
              label: "RadioGroup States",
              storyId: "reference-catalogue-actions-and-form-controls--radio-group-states",
            },
            {
              label: "Narrow Viewport",
              storyId: "reference-catalogue-actions-and-form-controls--narrow-viewport",
              note: "the under-560px behavior of the shared control styles",
            },
          ],
        },
      ]}
    />
  );
}
