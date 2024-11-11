"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./components/auth-provider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./components/ui/select";
import { Textarea } from "./components/ui/textarea";

const formSchema = z.object({
  name: z.string().min(2, { message: "Name must be at least 2 characters." }),
  age: z.string().regex(/^\d+$/, { message: "Age must be a number." }),
  gender: z.string().min(1, { message: "Gender is required." }),
  location: z
    .string()
    .min(2, { message: "Location must be at least 2 characters." }),
  occupation: z
    .string()
    .min(2, { message: "Occupation must be at least 2 characters." }),
  interests: z.string().regex(/^[a-zA-Z\s,]+$/, {
    message: "Interests must be a comma-separated list of words.",
  }),
  scenario: z
    .object({
      type: z.string().default("plan-vacation"),
      vacation_destination: z.string().optional(),
      vacation_explanation: z.string().optional(),
      description: z.string().optional(),
    })
    .refine(
      (data) => {
        if (data.type === "plan-vacation") {
          return !!(data.vacation_destination && data.vacation_explanation);
        } else if (data.type === "custom") {
          return !!data.description;
        }
        return true;
      },
      {
        message:
          "Please fill out the required fields for the selected scenario.",
        path: ["scenario.type"],
      }
    ),
  tone: z.string().min(1, { message: "Tone is required." }),
  personality: z.array(z.string()),
});

type FormValues = z.infer<typeof formSchema>;

function Register() {
  const { token, setAuth } = useAuth();
  const navigate = useNavigate();
  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      age: "",
      gender: "",
      location: "",
      occupation: "",
      interests: "",
      scenario: {
        type: "plan-vacation",
        vacation_destination: "",
        vacation_explanation: "",
        description: "",
      },
      tone: "",
      personality: [] as string[],
    },
  });

  const onSubmit = (data: FormValues) => {
    let scenario =
      `{agent} wants to plan a trip with {user}. Both of them are colleagues at ` +
      `work who recently met each other. {user} is ${data.age} years old and is a ${data.gender}. ` +
      `{user} is originally from ${data.location} {user}'s interests are; ` +
      `"${data.interests}". {agent} will use a ${data.tone} tone and will try to be ` +
      `${data.personality.join(", ")}. `;

    if (data.scenario.type === "plan-vacation") {
      scenario +=
        `{user} likes ${data.scenario.vacation_destination}, saying "${data.scenario.vacation_explanation}". In this conversation, ` +
        `{agent} will float the idea of planning a trip to ${data.scenario.vacation_destination}, discuss ` +
        `details/itinerary and convince {user} to join them.`;
    } else if (data.scenario.type === "custom") {
      scenario += data.scenario.description;
    } else {
      throw new Error("Invalid scenario type");
    }

    fetch(`${import.meta.env.VITE_API_URL}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ name: data.name, scenario }),
    })
      .then((res) => {
        if (res.ok) {
          return res.json();
        }
        throw new Error("Failed to register");
      })
      .then((user) => {
        setAuth({ token: token!, user });
        navigate("/chat");
      });
  };

  const scenarioType = form.watch("scenario.type");

  return (
    <div className="flex items-center justify-center w-screen">
      <div className="lg:w-3/5">
        <h1 className="text-3xl font-bold text-center m-8">
          Complete Your Registration
        </h1>
        <Form {...form}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              console.log("Submitting", form.getValues());
              form.handleSubmit(onSubmit)();
            }}
            className="space-y-8 bg-card p-6 rounded-lg shadow-md"
          >
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              {/* Name Field */}
              <div className="md:col-span-2">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <Input placeholder="John" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              {/* Age Field */}
              <div>
                <FormField
                  control={form.control}
                  name="age"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Age</FormLabel>
                      <FormControl>
                        <Input placeholder="26" {...field} type="number" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div>
                <FormField
                  control={form.control}
                  name="gender"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Gender</FormLabel>
                      <FormControl>
                        <Input placeholder="Male" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                {/* Location Field */}
                <FormField
                  control={form.control}
                  name="location"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Location</FormLabel>
                      <FormControl>
                        <Input placeholder="New York City" {...field} />
                      </FormControl>
                      <FormDescription>
                        Where you're originally from
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div>
                {/* Occupation Field */}
                <FormField
                  control={form.control}
                  name="occupation"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Occupation</FormLabel>
                      <FormControl>
                        <Input placeholder="Airline Pilot" {...field} />
                      </FormControl>
                      <FormDescription>
                        Your current job or a dream career if you prefer
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>
            {/* Interests Field */}
            <FormField
              control={form.control}
              name="interests"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Interests</FormLabel>
                  <FormControl>
                    <Input placeholder="Hiking, reading, cooking" {...field} />
                  </FormControl>
                  <FormDescription>
                    A comma-separated list of some things you enjoy
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Scenario Field */}
            <FormField
              control={form.control}
              name="scenario.type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Scenario</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="plan-vacation">
                        Plan a vacation with a colleague
                      </SelectItem>
                      <SelectItem value="custom">
                        Describe a custom scenario
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    A scenario that will be drive your conversation
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {scenarioType === "plan-vacation" && (
              <>
                {/* Vacation Destination Field */}
                <FormField
                  control={form.control}
                  name="scenario.vacation_destination"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Vacation Destination</FormLabel>
                      <FormControl>
                        <Input placeholder="Hawaii" {...field} />
                      </FormControl>
                      <FormDescription>
                        A place you'd like to visit or have visited
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="scenario.vacation_explanation"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Vacation Explanation</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="I love the beaches and the food!"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Why you'd like to visit or what you enjoyed about your
                        visit
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}

            {scenarioType === "custom" && (
              <FormField
                control={form.control}
                name="scenario.description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Scenario Description</FormLabel>
                    <FormControl>
                      <Textarea placeholder="" {...field} />
                    </FormControl>
                    <FormDescription>
                      Describe the scenario you'd like to use, using{" "}
                      <code>{"{agent}"}</code> and <code>{"{user}"}</code> as
                      placeholders
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {/* Tone Field */}
            <FormField
              control={form.control}
              name="tone"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Conversation Tone</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select tone" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="casual">Casual</SelectItem>
                      <SelectItem value="business">Business</SelectItem>
                      <SelectItem value="formal">Formal</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Choose a tone for the conversation style
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Personality Traits Field */}
            <FormField
              control={form.control}
              name="personality"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Personality Traits</FormLabel>
                  <div className="flex flex-wrap gap-4">
                    {[
                      "optimistic",
                      "open-minded",
                      "supportive",
                      "friendly",
                      "inquisitive",
                      "humorous",
                      "helpful",
                      "cooperative",
                      "reliable",
                      "weird",
                    ].map((trait) => (
                      <div key={trait} className="flex items-center space-x-2">
                        <Checkbox
                          checked={field.value.includes(trait)}
                          onCheckedChange={(checked) => {
                            const newTraits = checked
                              ? [...field.value, trait]
                              : field.value.filter((t) => t !== trait);
                            field.onChange(newTraits);
                          }}
                        />
                        <span>{trait}</span>
                      </div>
                    ))}
                  </div>
                  <FormDescription>
                    Select personality traits of the person you'd like to talk
                    to
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Submit Button */}
            <div className="flex justify-center">
              <Button type="submit" className="w-full py-3 rounded-lg">
                Complete Registration
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
}

export default Register;
